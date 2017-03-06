#-*- coding: utf-8 -*-
#qpy:kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.utils import platform
from kivy.clock import Clock

from bot_core import LongPollSession

from plyer import notification
import androidhelper as sl4a
droid = sl4a.Android()

Builder.load_string('''
#:import FadeTransition kivy.uix.screenmanager.FadeTransition
<Root>:
	id: rootscr
	transition: FadeTransition()
''')


class ChatBot(App):
	use_kivy_settings = False
	def __init__(self, *args, **kwargs):
		super(ChatBot, self).__init__(*args, **kwargs)
		self.root = Root()
	
	def on_stop(self):
		while not session.stop_bot(): continue

	def build(self):
		self.root.add_widget(HomeScreen())
		self.root.add_widget(LoginScreen())
		
		activation_status = self.config.getdefault('General', 'bot_activated', 'False')
		global session
		session = LongPollSession(activated=activation_status == 'True')

		if not session.authorization():
			self.root.show_auth_form()

		return self.root

	def on_pause(self):
		return True
		
	def build_config(self, config):
		config.setdefaults('General', 
				{'show_bot_activity':'False', "bot_activated":'False', 'custom_commands':'False'}
			)

	def build_settings(self, settings):
		settings.add_json_panel("Настройки бота", self.config, data=
			'''[
				{"type": "bool",
				"title": "Отображать состояние бота в статусе",
				"section": "General",
				"key": "show_bot_activity",
				"values": ["False","True"],
				"disabled": 1
				},
				{"type": "bool",
				"title": "Использоаать пользовательские команды (WIP)",
				"section": "General",
				"key": "custom_commands",
				"values": ["False","True"]
				},
				{"type": "bool",
				"title": "Бот активирован",
				"section": "General",
				"key": "bot_activated",
				"values": ["False","True"],
				"disabled": 1
				}
			]'''
		)

class LoginScreen(Screen):
	def log_in(self):
		droid.dialogCreateSpinnerProgress('Авторизация. Пожалуйста, подождите', 'Это может занять несколько секунд')
		droid.dialogShow()

		login = self.ids.login.text
		password = self.ids.pass_input.text

		if login and password:
			if session.authorization(login=login, password=password):
				self.parent.show_home_form()
			else:
				droid.makeToast('Неверный логин или пароль')

		self.ids.pass_input.text = ''
		droid.dialogDismiss()


class HomeScreen(Screen):
	def __init__(self, *args, **kwargs):
		super(HomeScreen, self).__init__(*args, **kwargs)
		self.bot_check_event = Clock.schedule_interval(self.check_if_bot_active, 1)
		self.run_bot_text = 'Включить бота'
		self.stop_bot_text = 'Выключить бота'
		self.ids.main_btn.text = self.run_bot_text

	def on_main_btn_press(self):
		config = ChatBot.get_running_app().config

		if self.parent.current_screen.ids.main_btn.text == self.run_bot_text:
			self.start_bot(config)
		else:
			self.stop_bot(config)

		#self.update_answers_count()

	def start_bot(self, config):
		self.activation_status = config.getdefault('General', 'bot_activated', 'False')
		use_custom_commands = config.getdefault('General', 'custom_commands', 'False')

		while not session.start_bot(activated=self.activation_status == 'True',\
			use_custom_commands=use_custom_commands == 'True'): continue

		self.ids.main_btn.text = self.stop_bot_text
		self.bot_check_event()
		notification.notify(title='VKBot',message='Bot active')

	def stop_bot(self, config):
		self.bot_check_event.cancel()
		bot_stopped = False

		while not bot_stopped:
			bot_stopped, new_activation_status = session.stop_bot()

		if new_activation_status != self.activation_status:
			config.set('General', 'bot_activated', str(new_activation_status))
			config.write()

		self.ids.main_btn.text = self.run_bot_text
		notification.notify(title='VKBot',message='Bot stopped')

	def update_answers_count(self):
		self.ids.answers_count_lb.text = 'Ответов: {}'.format(session.reply_count)

	def logout(self):
		session.authorization(logout=True)
		self.parent.show_auth_form()
	
	def check_if_bot_active(self, _):
		if not session.running:
			self.ids.main_btn.text = self.run_bot_text
			self.bot_check_event.cancel()

class Root(ScreenManager):
	def show_auth_form(self):
		self.current = 'login_screen'
		self.current_screen.ids.pass_auth.disabled = not session.authorized
		
	def show_home_form(self):
		self.current = 'home_screen'


if __name__ == '__main__':
	ChatBot().run()