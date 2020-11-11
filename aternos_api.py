import argparse
import atexit
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait

parser = argparse.ArgumentParser(description='Aternos API')

parser.add_argument("-v", "--verbose", help="show timed actions", action="store_true")
args = parser.parse_args()
verbose = args.verbose


def sleep(t, nom=""):
	if verbose:
		print(nom)
	t = t * 10
	for i in range(int(t)):
		if verbose:
			print(str(i / 10 + 0.1)[0:3], end="\r", flush=True)
		time.sleep(0.1)
	if verbose:
		print("\n")


class LoginError(Exception):
	pass


class Player(object):
	def __init__(self, name):
		self.name = name

	def eject(self):
		"""TODO eject"""

	def ban(self):
		"""TODO eject"""

	def op(self):
		"""TODO eject"""


class Account(object):
	servers: "[Server]"
	_servers: "[Server]"

	def __init__(self, user, password):
		self.user = user
		self.password = password
		options = Options()
		options.headless = True
		self.driver = webdriver.Firefox(firefox_binary="/app/vendor/geckodriver/geckodriver",options=options)

		self.driver.implicitly_wait(10)
		self.driver.set_window_rect(**{'x': 1912, 'y': 295, 'width': 1382, 'height': 744})
		self._servers = None
		self.login()
		atexit.register(self.close)

	def login(self):
		self.driver.get("https://aternos.org/go/")
		sleep(0.1, "get url")

		usr_input = self.driver.find_element_by_id("user")
		pass_input = self.driver.find_element_by_id("password")
		login_btn = self.driver.find_element_by_id("login")
		error = self.driver.find_element_by_class_name("login-error")

		usr_input.click()
		sleep(0.1, "get usr field")

		usr_input.send_keys(self.user)
		sleep(0.1, "send usr keys")

		pass_input.click()
		sleep(0.1, "get pass field")

		pass_input.send_keys(self.password)
		sleep(0.1, "send pass keys")

		login_btn.click()
		sleep(0.5, "wait for login")
		if "server" not in self.driver.current_url:
			error_text = error.text.strip()
			if error_text:
				raise LoginError(error_text)
		self.fetch_servers()
		if "servers" in self.driver.current_url:
			self.driver.find_elements_by_class_name("server-body")[0].click()
			sleep(0.5, "select server")
			self.driver.find_element_by_id("accept-choices").click()
			sleep(2, "accept cookies")

	def is_logged_in(self):
		return self.driver.get_cookie("ATERNOS_SESSION") is not None

	def fetch_servers(self):
		if "servers" not in self.driver.current_url:
			self.driver.get("https://aternos.org/servers/")
		servers = self.driver.find_elements_by_class_name("server-infos")
		servers_objets = []
		for server in servers:
			server_name = server.find_element_by_class_name("server-name").text.strip()
			server_id = server.find_element_by_class_name("server-id").text[1:].strip()
			server_version = server.find_element_by_class_name("server-software").text.strip()
			try:
				server_author = server.find_element_by_class_name("server-by-user")
				server_author = server_author.text.split(" ")[-1:][0].strip()
			except NoSuchElementException:
				server_author = self.user
			servers_objets.append(
				Server(
					server_author,
					self,
					server_id,
					server_name
				)
			)
		self._servers = servers_objets

	def close(self):
		self.driver.close()

	@property
	def servers(self):
		if self._servers is None:
			self.fetch_servers()
		return self._servers


# noinspection SpellCheckingInspection
class Server(object):
	def __init__(self, author: str, account: Account, id:str = None, name:str = None):
		self.account             = account
		self._status: str        = ""
		self.version_type: str   = ""
		self.version: str        = ""
		self.author: str         = author
		self.id: str             = id
		self._connect_ip: str    = ""
		self.port: int           = 0
		self.name: str           = name
		self.ip: str             = ""
		self.max_players: int    = 0
		self._player_count: int  = 0
		self._players: [Player]  = []
		self._countdown: int     = 0
		self.motd: str           = ""
		self.ram: int            = 0

	@property
	def players(self):
		# self.fetch()
		return self._players

	@property
	def status(self):
		# self.fetch()
		return self._status

	@property
	def player_count(self):
		# self.fetch()
		return self._players

	@property
	def connect_ip(self):
		# self.fetch()
		return self._connect_ip

	@property
	def countdown(self):
		# self.fetch()
		return self._countdown

	def _go_to_the_good_server(self):
		if not self.account.is_logged_in():
			self.account.login()
		cookie = self.account.driver.get_cookie("ATERNOS_SERVER")
		if cookie["value"] != self.id:
			cookie["value"] = self.id
			self.account.driver.delete_cookie("ATERNOS_SERVER")
			self.account.driver.add_cookie(cookie)
			self.account.driver.refresh()

	def fetch(self):
		self._go_to_the_good_server()
		self.account.driver.execute_script("""
			window.__my_status = undefined;
			$.ajax({
				type: "get",
				url: buildURL("/panel/ajax/status.php", {}),
			}).then((e) => {
				window.__my_status = JSON.parse(e);
			});
			
			""")
		wait = WebDriverWait(self.account.driver, 10)
		result = wait.until(
			lambda driver: self.account.driver.execute_script("return window.__my_status;"))

		self.version_type  = result["type"]
		self.version       = result["version"]
		self.id            = result["id"]
		self._connect_ip   = result["host"]
		self.port          = result["port"]
		self.name          = result["name"]
		self.ip            = result["ip"]
		self.max_players   = result["slots"]
		self._player_count = result["players"]
		self._players      = [Player(name) for name in result["playerlist"]]
		self._countdown    = result["countdown"]
		self.motd          = result["motd"]
		self.ram           = result["ram"]
		self._status       = result["lang"]

	# def fetch(self):
	# 	self._go_to_server_main_page()
	# 	self.ip = self.account.driver.find_element_by_class_name("server-ip").text.split("\n")[0]
	# 	self._go_to_server_settings()
	# 	self.max_players = self.account.driver.find_element_by_name("max-players").get_attribute("value")

	def __str__(self):
		return f"server {self.name} from {self.author}"

	def __repr__(self):
		return f"<{self.__str__()}>"

	def _go_to_server_settings(self):
		self._go_to_server_main_page()
		if self.account.driver.current_url != "https://aternos.org/options/":
			self.account.driver.get("https://aternos.org/options/")

	def _go_to_server_main_page(self):
		self._go_to_the_good_server()
		if self.account.driver.current_url != "https://aternos.org/server/":
			self.account.driver.get("https://aternos.org/server/")

	def start(self):
		self._go_to_server_main_page()
		start = self.account.driver.find_element_by_id("start")
		restart = self.account.driver.find_element_by_id("restart")
		if restart.is_displayed():
			restart.click()
		else:
			start.click()
