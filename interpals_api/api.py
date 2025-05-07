import json
import asyncio
from urllib.parse import urlencode, urlparse, parse_qs
from time import sleep

import requests
import aiohttp
from bs4 import BeautifulSoup
import re

from .lib.errors import *
from .lib.cookie import Cookie
from .utils import find_csrf_token
from .parsers.profile_parser import ProfileParser
from .parsers.chat_parser import ChatParser
from .parsers.friends_parser import FriendsParser
from .parsers.pictures_parser import PicturesParser


class Api:
    timeout = 3.0
    host = "interpals.net"
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " \
                 "(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"

    def __init__(self, session):
        self._session = session

    def check_auth(self):
        if self._session:
            response = self._get(self._session.username)
            return self._check_body_for_auth(response.text)
        else:
            return False

    def view(self, user):
        self._get(user, check_auth=True)

    def profile(self, user):
        response = self._get(user, check_auth=True)

        if "User not found." in response.text:
            raise APIError("user not found")

        parser = ProfileParser()
        data = parser.parse(response.text)

        return data

    def visitors(self):
        response = self._get("/app/views", check_auth=True)
        soup = BeautifulSoup(response.text, "lxml")
        items = soup.find_all('div', class_='vBottomTxt')
        users = []
        for item in items:
            user = item.find('a')['href'][1:].split('?')[0]
            users.append(user)
        return users

    def search(self, options, limit=1000, timeout=0.0):
        response = self._get("/app/search", check_auth=True)
        csrf_token = find_csrf_token(response.text)

        offset = 0
        params = self._prepare_search_params(options)
        params['csrf_token'] = csrf_token
        while True:
            params['offset'] = str(offset)

            response = self._get("/app/search", params, check_auth=True)
            users = self._parse_search_result(response.text)

            if not users:
                return

            for user in users:
                yield user
                offset += 1
                if offset >= limit:
                    return

            sleep(timeout)

    def get_uid(self, user):
        profile_info = self.profile(user)
        return profile_info['uid']

    def get_thread_id(self, uid):
        params = {'action': 'send', 'uid': uid}
        response = self._get("/pm.php", params)
        assert response.status_code == 301

        location = response.headers['Location']
        thread_id = parse_qs(urlparse(location).query)['thread_id'][0]

        return thread_id

    def chat(self, count=9, offset=0):
        chat_parser = ChatParser()

        response = self._get("/pm.php", check_auth=True)
        maxmsgid = chat_parser.parse_maxmsgid(response.text)
        unread = chat_parser.parse_unread(response.text)

        chats = []
        while len(chats) < count:
            params = {
                'action': 'more_threads',
                'from': str(offset),
                'filter': 'all',
                'max_msg_id': maxmsgid,
            }
            response = self._post("/pm.php", params)
            body = response.json()['body']

            items = chat_parser.parse_chat(body)
            if not items:
                break

            for item in items:
                chats.append(item)
                if len(chats) >= count:
                    break

            offset += len(items)

        return {
            'chats': chats,
            'unread': unread
        }

    def chat_messages(self, thread_id, last_msg_id=None):
        params = {
            'action': 'load_messages',
            'thread': thread_id
        }
        if last_msg_id:
            params['last_msg_id'] = last_msg_id

        response = self._post("/pm.php", params)
        body = response.json()['body']

        chat_parser = ChatParser()
        messages = chat_parser.parse_messages(body)

        return messages

    def chat_send(self, thread_id, message):
        params = {
            'action': 'send_message',
            'thread': thread_id,
            'message': message
        }
        response = self._post("/pm.php", params)
        assert '"error"' not in response.text, response.text

    def chat_delete(self, thread_id):
        params = {
            'action': 'delete_thread',
            'thread': thread_id,
            'block_user': '0'
        }
        self._post("/pm.php", params)

    def friends(self, uid):
        url = "/app/friends?uid={}".format(uid)
        response = self._get(url, check_auth=True)
        friends_parser = FriendsParser()
        items = friends_parser.parse(response.text)
        return items

    def friend_add(self, uid):
        url = "/app/friends/add?uid={}".format(uid)
        response = self._get(url)
        if response.status_code != 302:
            raise APIError("could not add user")

    def friend_remove(self, uid):
        url = "/app/friends/delete?uid={}".format(uid)
        response = self._get(url)
        if response.status_code != 302:
            raise APIError("could not delete user")

    def albums(self, uid):
        response = self._get("/app/albums", {'uid': uid}, check_auth=True)
        pictures_parser = PicturesParser()
        items = pictures_parser.parse_albums(response.text)
        return items

    def pictures(self, uid, aid):
        response = self._get("/app/album", {'uid': uid, 'aid': aid}, check_auth=True)
        pictures_parser = PicturesParser()
        items = pictures_parser.parse_pictures(response.text)
        return items

    @classmethod
    def _get_full_url(cls, url, params=None):
        if not url.startswith("/"):
            url = "/" + url
        url = "https://{}{}".format(cls.host, url)
        if params is not None:
            url += '?' + urlencode(params, True)
        return url

    def _get(self, url, params=None, check_auth=False):
        headers = self._get_headers()
        if params is not None:
            url = url + '?' + urlencode(params, True)
        full_url = self._get_full_url(url)
        response = requests.get(full_url, headers=headers, timeout=self.timeout, allow_redirects=False)
        if check_auth and not self._check_body_for_auth(response.text):
            raise APIAuthError()
        return response

    def _post(self, url, params, check_auth=False):
        headers = self._get_headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        full_url = self._get_full_url(url)
        response = requests.post(full_url, data=params, headers=headers, timeout=self.timeout, allow_redirects=False)
        if check_auth and not self._check_body_for_auth(response.text):
            raise APIAuthError()
        return response

    def _get_headers(self):
        cookie = Cookie()
        cookie.update(self._session.cookie())
        headers = {
            'Cookie': cookie.as_string(),
            'User-Agent': self.user_agent
        }
        return headers

    def _check_body_for_auth(self, body):
        return "/app/auth/logout" in body

    def _prepare_search_params(self, options):
        params = {
            'offset': '',
            'sort': 'last_login',
            'age1': options.get('age1', '16'),
            'age2': options.get('age2', '110'),
            'sex[]': options.get('sex', ['male', 'female']),
            'continents[]': options.get('continents', ['AF', 'AS', 'EU', 'NA', 'OC', 'SA']),
            'countries[]': options.get('countries', ['---']),
            'languages[]': ['---'],
            'lfor[]': [
                'lfor_email', 'lfor_snail', 'lfor_langex',
                'lfor_friend', 'lfor_flirt', 'lfor_relation'
            ],
            'keywords': options.get('keywords', ''),
            'username': '',
            'csrf_token': 'ZjU1ZWZkM2Q=',
        }

        if options.get('online'):
            params['online'] = '1'

        if options.get('photo'):
            params['photo'] = '1'

        if options.get('cityName'):
            citycode = options.get('city')
            cityname = options.get('cityName')
            if not citycode:
                citycode = self._get_citycode(cityname)
            params['city'] = citycode
            params['cityName'] = cityname

        return params

    def _parse_profile(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'lxml')
        profile = {}

        # 1. Name and Age
        header = soup.select_one('.profileBox h1')
        profile['username'] = ''
        profile['name'] = ''
        profile['age'] = ''
        if header:
            profile['username'] = header.text.strip()  # Username, e.g., "Absonoplyanka"
            
            name_age_text_node = header.next_sibling
            if name_age_text_node and isinstance(name_age_text_node, str):
                name_age_text = name_age_text_node.strip()  # e.g., "Antoine,  28 y.o."
                
                parts = name_age_text.split(',', 1) # Split only on the first comma
                if parts:
                    profile['name'] = parts[0].strip() # Real name, e.g., "Antoine"
                
                age_match = re.search(r'(\d+)\s*y\.o\.', name_age_text)
                if age_match:
                    profile['age'] = age_match.group(1)  # e.g., "28"
                elif len(parts) > 1: # Fallback if regex fails but comma split provided a second part
                    age_candidate = parts[1].replace('y.o.', '').strip()
                    age_digits_match = re.match(r'(\d+)', age_candidate)
                    if age_digits_match:
                        profile['age'] = age_digits_match.group(1)

        # 2. Gender (based on the icon)
        # This logic assumes only male icon is explicitly checked. If female icon exists, it's female.
        # If neither, it defaults to 'Female'. This could be made more robust if specific female icon exists.
        gender_icon = soup.select_one('.profileBox img[src*="male-14.png"]')
        profile['gender'] = 'Male' if gender_icon else 'Female'

        # 3. Locations
        # Corrected to remove "[Current City]" and "[Hometown]" tags from the text.
        location_elements = soup.select('.profLocation .profDataTopData')
        if location_elements:
            current_city_text_container = location_elements[0].select_one('div[style*="float: left"]')
            if current_city_text_container:
                # Create a temporary copy to manipulate for text extraction
                temp_container = BeautifulSoup(str(current_city_text_container), 'lxml').div
                span_tag = temp_container.select_one('span[style*="color: #ccc;"]')
                if span_tag:
                    span_tag.decompose() # Remove the "[Current City]" like span
                profile['current_city'] = temp_container.get_text(separator=' ', strip=True).rstrip(',').strip()
            else: # Fallback if inner div not found
                 raw_text = location_elements[0].get_text(separator=' ', strip=True)
                 profile['current_city'] = raw_text.replace('[Current City]', '').strip().rstrip(',')


        if len(location_elements) > 1:
            hometown_text_container = location_elements[1].select_one('div[style*="float: left"]')
            if hometown_text_container:
                temp_container = BeautifulSoup(str(hometown_text_container), 'lxml').div
                span_tag = temp_container.select_one('span[style*="color: #ccc;"]')
                if span_tag:
                    span_tag.decompose() # Remove the "[Hometown]" like span
                profile['hometown'] = temp_container.get_text(separator=' ', strip=True).rstrip(',').strip()
            else: # Fallback
                raw_text = location_elements[1].get_text(separator=' ', strip=True)
                profile['hometown'] = raw_text.replace('[Hometown]', '').strip().rstrip(',')


        # 4. Languages
        # Revised to avoid CSS pseudo-selectors :has and :contains for broader compatibility & clarity.
        def get_languages_revised(parent_selector_class, h3_text_to_find):
            langs = []
            possible_sections = soup.select(f'.{parent_selector_class}')
            for section_candidate in possible_sections:
                h3 = section_candidate.find('h3')
                if h3 and h3_text_to_find.lower() in h3.text.lower():
                    for lang_element in section_candidate.select('.profLang'):
                        name_tag = lang_element.select_one('.prLangName')
                        level_img = lang_element.select_one('.proflLevel')
                        if name_tag:
                            name = name_tag.get_text(strip=True).replace('\n', ' ')
                            level = None
                            if level_img and level_img.has_attr('src'):
                                level_src = level_img['src']
                                level = level_src.split('/')[-1].replace('.png', '')
                            langs.append({'name': name, 'level': level})
                    break # Found the correct section
            return langs

        profile['speaks'] = get_languages_revised('profDataTopField', 'Speaks')
        profile['learning'] = get_languages_revised('profDataTopField', 'Learning')

        # 5. Looking for
        # Revised similarly to languages to avoid CSS pseudo-selectors.
        looking_for_items = []
        possible_lf_sections = soup.select('.profDataTopField')
        for section_candidate in possible_lf_sections:
            h3 = section_candidate.find('h3')
            if h3 and "looking for" in h3.text.lower():
                looking_for_tags = section_candidate.select('.lfor')
                looking_for_items = [tag.text.strip() for tag in looking_for_tags]
                break
        profile['looking_for'] = looking_for_items

        # 6. About / Requests / Hobbies etc.
        # Corrected to reliably find sections by H2 text, removing the faulty icon-class based selector.
        data_sections = {
            'about': 'About',
            'requests': 'Requests',
            'hobbies': 'Hobbies & Interests', # Note: HTML has "Hobbies & Interests"
            'music': 'Favorite Music',
            'movies': 'Favorite Movies',
            'tv_shows': 'Favorite TV Shows',
            'books': 'Favorite Books',
        }

        for key, heading_text_to_find in data_sections.items():
            section_h2 = None
            h2_candidates = soup.select('.profDataBox h2') # Search H2s only within .profDataBox
            for h2_candidate in h2_candidates:
                # Extract text part of H2, which usually follows an <i> icon tag
                icon_tag = h2_candidate.find('i')
                actual_text_in_h2 = ""
                if icon_tag and icon_tag.next_sibling and isinstance(icon_tag.next_sibling, str):
                    actual_text_in_h2 = icon_tag.next_sibling.strip()
                elif not icon_tag: # If no icon tag, use the full text
                     actual_text_in_h2 = h2_candidate.text.strip()
                
                # Check if the found text matches the heading we are looking for
                if actual_text_in_h2.lower() == heading_text_to_find.lower():
                    section_h2 = h2_candidate
                    break
                elif not actual_text_in_h2 and heading_text_to_find.lower() in h2_candidate.text.lower():
                    # Fallback: if direct text extraction failed but heading is in the h2's full text
                    section_h2 = h2_candidate
                    break


            if section_h2:
                box_text_div = section_h2.find_next_sibling('div', class_='profDataBoxText')
                if box_text_div:
                    profile[key] = box_text_div.get_text(separator=' ', strip=True)
        return profile

    def _parse_search_result(self, body):
        users = []
        soup = BeautifulSoup(body, "lxml")
        results = soup.find_all('div', class_='sResInner')

        for item in results:
            try:
                # Main section
                main = item.find('div', class_='sResMain')
                username_tag = main.find('b').find('a') if main else None
                username = username_tag.text.strip() if username_tag else ''

                # Gender
                sex_img = item.find('img', class_='sResSex')
                gender = 'Male' if sex_img and 'male' in sex_img['src'].lower() else 'Female' if sex_img and 'female' in sex_img['src'].lower() else 'Unknown'

                # Location
                location_city = ''
                location_country = ''
                location_links = main.find_all('a', href=True) if main else []

                for tag in location_links:
                    href = tag['href']
                    if 'city=' in href:
                        location_city = tag.text.strip()
                    elif 'countries[]=' in href:
                        location_country = tag.text.strip()

                # Profile image
                thumb = item.find('a', class_='sResThumb')
                profile_img = thumb.find('img')['src'] if thumb and thumb.find('img') else ''

                # Joined
                joined_tag = item.find('div', class_='sResJoined')
                joined = joined_tag.text.strip() if joined_tag else ''

                # Status
                status_tag = item.find('div', class_='sResLastOnline')
                online_now = 'Online now' in status_tag.text if status_tag else False

                # Description
                description_tag = item.find('div', class_='sResMainTxt')
                description_field = description_tag.find('div', class_='sResTxtField') if description_tag else None
                description = description_field.text.strip() if description_field else ''

                user_data = {
                    'username': username,
                    'gender': gender,
                    'location_city': location_city,
                    'location_country': location_country,
                    'joined': joined,
                    'online_now': online_now,
                    'profile_image': profile_img,
                    'description': description,
                }

                users.append(user_data)

            except Exception as e:
                print(f"Error parsing a user block: {e}")

        return users

    def _get_citycode(self, cityname):
        response = self._get("/app/async/geoAc", {"query": cityname})
        data = response.json()
        return data['items'][0]['id']


class ApiAsync(Api):
    async def check_auth(self):
        if self._session:
            try:
                await self._request(self._session.username)
            except APIAuthError:
                return False
            else:
                return True
        else:
            return False

    async def view(self, user):
        body = await self._request(user)
        return self._parse_profile(body)
        

    async def profile(self, user):
        html = await self._request(user)

        if "User not found." in html:
            raise APIError("User not found")

        if "Sorry, this user's privacy settings do not allow " \
                "you to contact them." in html:
            raise APIError("Blocked by user")

        parser = ProfileParser()
        data = parser.parse(html)

        return data

    async def visitors(self):
        html = await self._request("/app/views")
        soup = BeautifulSoup(html, "lxml")
        items = soup.find_all('div', class_='vBottomTxt')
        users = []
        for item in items:
            user = item.find('a')['href'].split('?')[0][1:]
            users.append(user)
        return users

    async def search(self, options, limit=1000, timeout=0.0):
        html = await self._request("/app/search")
        csrf_token = find_csrf_token(html)

        offset = 0
        params = self._prepare_search_params(options)
        params['csrf_token'] = csrf_token
        while True:
            params['offset'] = str(offset)

            html = await self._request("/app/search", params=params)
            users = self._parse_search_result(html)

            if not users:
                return

            for user in users:
                yield user
                offset += 1
                if offset >= limit:
                    return

            await asyncio.sleep(timeout)

    async def get_uid(self, user):
        profile_info = await self.profile(user)
        return profile_info['uid']

    async def get_thread_id(self, uid):
        params = {'action': 'send', 'uid': uid}

        try:
            await self._request("/pm.php", params=params)
        except APIRedirectError as exc:
            location = exc.args[1]
            thread_id = parse_qs(urlparse(location).query)['thread_id'][0]
            return thread_id
        else:
            raise APIError("Could not load thread_id")

    async def chat(self, count=9, offset=0):
        chat_parser = ChatParser()

        html = await self._request("/pm.php")
        maxmsgid = chat_parser.parse_maxmsgid(html)
        unread = chat_parser.parse_unread(html)

        chats = []
        while len(chats) < count:
            params = {
                'action': 'more_threads',
                'from': str(offset),
                'filter': 'all',
                'max_msg_id': maxmsgid,
            }

            text = await self._request("/pm.php", params=params, method='post', 
                                       check_auth=False)
            body = json.loads(text)['body']

            items = chat_parser.parse_chat(body)
            if not items:
                break

            for item in items:
                chats.append(item)
                if len(chats) >= count:
                    break

            offset += len(items)

        return {
            'chats': chats,
            'unread': unread
        }

    async def chat_messages(self, thread_id, last_msg_id=None):
        params = {
            'action': 'load_messages',
            'thread': thread_id
        }
        if last_msg_id:
            params['last_msg_id'] = last_msg_id

        text = await self._request("/pm.php", params=params, method='post', 
                                   check_auth=False)
        body = json.loads(text)['body']

        chat_parser = ChatParser()
        messages = chat_parser.parse_messages(body)

        return messages

    async def chat_send(self, thread_id, message):
        params = {
            'action': 'send_message',
            'thread': thread_id,
            'message': message
        }
        text = await self._request("/pm.php", params=params, method='post', 
                                   check_auth=False)
        if '"error"' in text:
            raise APIError(text)

    async def chat_delete(self, thread_id):
        params = {
            'action': 'delete_thread',
            'thread': thread_id,
            'block_user': '0'
        }
        await self._request("/pm.php", params=params, method='post', 
                            check_auth=False)

    async def friends(self, uid):
        url = "/app/friends?uid={}".format(uid)
        html = await self._request(url)
        friends_parser = FriendsParser()
        items = friends_parser.parse(html)
        return items

    async def friend_add(self, uid):
        url = "/app/friends/add?uid={}".format(uid)
        try:
            await self._request(url)
        except APIRedirectError:
            pass
        else:
            raise APIError("Could not add friend")

    async def friend_remove(self, uid):
        url = "/app/friends/delete?uid={}".format(uid)
        try:
            await self._request(url)
        except APIRedirectError:
            pass
        else:
            raise APIError("Could not delete friend")

    async def albums(self, uid):
        html = await self._request("/app/albums", params={'uid': uid})
        pictures_parser = PicturesParser()
        items = pictures_parser.parse_albums(html)
        return items

    async def pictures(self, uid, aid):
        html = await self._request("/app/album", 
                                   params={'uid': uid, 'aid': aid})
        pictures_parser = PicturesParser()
        items = pictures_parser.parse_pictures(html)
        return items

    async def _request(self, url, method='get', params=None, check_auth=True):
        assert method in ('get', 'post')

        full_url = self._get_full_url(url, params if method == 'get' else None)
        headers = self._get_headers()

        if method == 'post':
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        kwargs = {
            'url': full_url,
            'headers': headers,
            'timeout': self.timeout,
            'allow_redirects': False,
        }

        if method == 'post':
            kwargs['data'] = params

        async with aiohttp.ClientSession() as session:
            request_func = session.post if method == 'post' else session.get
            async with request_func(**kwargs) as resp:
                if resp.status in (301, 302):
                    raise APIRedirectError(
                        resp.status, resp.headers['Location']
                    )
                body = await resp.text()

        if check_auth and not self._check_body_for_auth(body):
            raise APIAuthError()
        
        return body
