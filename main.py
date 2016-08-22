import random
import colorama
from colorama import Fore, Back, Style
import threading
import msvcrt
import time

time_limit = 20
time_limit_part = 3
time_limit_after = 3

def current_time():
	return time.time()

import enum 
class State(enum.IntEnum):
	before = 1
	game = 2
	last_part = 3
	last_second = 4
	finished_round = 5
	finished_game = 6
state = State.before

colorama.init()
def header(text):
	is_digit = False
	result = Fore.GREEN
	for c in text:
		if c.isdigit() and (not is_digit):
			is_digit = True
			result += Fore.LIGHTGREEN_EX
		elif (not c.isdigit()) and is_digit:
			is_digit = False
			result += Fore.GREEN
		result += c	
	return result + colorama.Style.RESET_ALL
def colored(color, text):
	return color + text + colorama.Style.RESET_ALL
	
def call_main(callback=None):
	global lock_call_main, lock_main, main_callback
	lock_call_main.acquire()
	main_callback = callback
	lock_main.release()

timer_event = threading.Event()
def call_timer(seconds):
	global timer_stamp
	timer_stamp = seconds
	timer_event.clear()
	lock_timer.release()

f_new_word = False	
f_start_game = False
f_finish_round = False
def interaction_with_user():
	global lock_interaction, f_killed, f_new_word, f_start_game, f_finish_round
	while True:
		lock_interaction.acquire()
		code = ord(msvcrt.getch())
		#print('interaction_with_user: %d (%d)' % (code, ord('q')))
		if (code == 27) or (code == 3): f_killed = True # ESC, Ctrl+C
		if code == 13: f_start_game = True # Enter
		if code == 32: f_new_word = True   # Space
		if (code == ord('q')) or (code == ord('Q')): f_finish_round = True   # 'q'|'Q'
		call_main(lock_interaction)

f_timer_finish = False
def time_process():
	global lock_timer, timer_stamp, f_timer_finish 
	while True:
		lock_timer.acquire()
		#print('\nstart timer on %d seconds' % timer_stamp)
		timer_event.wait(timer_stamp)
		#print("timer: BREAKED {0}".format(timer_event.is_set()));
		f_timer_finish = True
		call_main()

config = {}
for s in open('config.txt').readlines():
	a, b = s.split()
	config[b] = a
k = int(config["number_of_words"])
players = int(config["number_of_players"])
time_limit = int(config["time_limit"])
names = [config["name" + str(i + 1)] for i in range(players)]
max_name_length = max(map(lambda x : len(x), names))
score1 = [0] * players
score2 = [0] * players

import zlib     
s = zlib.decompress(open('word_rus.zlib', 'rb').read()).decode('utf-8').split('\n')
n = len(s)
p = sorted([random.randint(0,n-k) for i in range(k)])
p = list(map(lambda x: s[sum(x)].strip(), enumerate(p)))

print(header("Всего %d слов. На ход %d секуд." % (k, time_limit)))

lock_timer = threading.Lock()
lock_main = threading.Lock()
lock_call_main = threading.Lock()
lock_interaction = threading.Lock()
lock_interaction.acquire()
lock_timer.acquire()
lock_call_main.acquire()
f_killed = False
main_callback = lock_interaction

threading.Thread(target=interaction_with_user, daemon=True).start()
threading.Thread(target=time_process, daemon=True).start()

def up(s, l):
	return s + ' ' * (l - len(s))

def print_in_same_place(text):
	print('\r' + up(text, 75), end="")

last_done = -1
who = 0
who_step = 1
player1 = 0
player2 = 1

def finish_round():
	global done, last_done, state, player1, player2, who, who_step, max_name_length
	score1[player1] += done
	score2[player2] += done
	last_done = done
	state = State.before
	if last_done != -1:
		print_in_same_place("%-*s --> %-*s : %d слов" % (max_name_length, names[player1], max_name_length, names[player2], last_done))
		print()	
	who = (who + 1) % players
	if who == 0:
		who_step = (who_step + 1) % players
		if who_step == 0:
			who_step += 1
	player1 = who
	player2 = (who + who_step) % players
	
while not f_killed:
	lock_main.acquire()
	status = ''
	
	#print('\nstate = %d : ' % state, end="")
	if f_timer_finish:
		f_timer_finish = False
		if state == State.game:
			state = State.last_part
			call_timer(time_limit_part)
		elif state == State.last_part:
			state = State.last_second
			call_timer(time_limit_after)
		elif state == State.last_second:
			state = State.finished_round
			
	if f_new_word:
		f_new_word = False
		if (State.game <= state) and (state <= State.finished_round):
			done += 1
			p.remove(word)
			if len(p) > 0:
				word = random.choice(p)
				if (State.last_second <= state) and (state <= State.finished_round):
					finish_round()
			else:
				finish_round()
				f_killed = True
				state = State.finished_game
				
	if f_start_game:
		f_start_game = False
		#print('[start] ', end="");
		if state == State.before:
			state = State.game
			call_timer(time_limit - time_limit_part)
		elif state == State.finished_round:
			finish_round()

	if f_killed and (State.game <= state) and (state <= State.finished_round):
		finish_round()

	if f_finish_round:
		f_finish_round = False
		timer_event.set()
		finish_round()
	#print('state = %d : ' % state)
	
	max_word_length = 20
	if state == State.before:
		done = 0
		word = random.choice(p)
		status = '%s --> %s. Осталось %d слов.' % (names[player1], names[player2], len(p))
		#if last_done != -1:
		#	status += ' В последнем раунде угадано %d слов.' % last_done
		status += ' Нажмите ENTER.'
	elif state == State.game:
		status = up(word, max_word_length)
		if done > 0:
			status += '[угадано %d слов]' % done
	elif state == State.last_part:
		status = up(word, max_word_length) + colored(Fore.YELLOW, "[последние %d секунд]" % time_limit_part)
	elif state == State.last_second:
		status = up(word, max_word_length) + colored(Fore.RED, "[время вышло, ваше последнее слово?]")
	elif state == State.finished_round:
		status = up(word, max_word_length) + colored(Fore.RED, "[раунд завершён, нажмите ENTER или SPACE]")
	elif state == State.finished_game:
		status = 'Все слова угаданы'
	else:
		status = 'error: invalid state'
		
	print_in_same_place(status)
	
	if main_callback != None:
		main_callback.release()
	lock_call_main.release()

print()
print(colored(Fore.GREEN, "%-*s : sum = объяснил + угадал" % (max_name_length, "Имя")))
for i in range(players):
	print("%-*s : %2d = %2d + %2d" % (max_name_length, names[i], score1[i] + score2[i], score1[i], score2[i]))
if state == State.finished_game:
	input()
