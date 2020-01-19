import time
import curses
import asyncio
import random
import os
import itertools
from fire_animation import fire
from curses_tools import draw_frame, read_controls, get_frame_size
from space_garbage import fly_garbage, obstacles_actual
from physics import update_speed


TIC_TIMEOUT = 0.1
SYMBOLS = ['+', '*', '.', ':']

def get_frames_from_dir(directory_with_frames):
    frames = []
    for frame_file in os.listdir(f"{directory_with_frames}"):
        with open(f"{directory_with_frames}/{frame_file}") as _file:
            frames.append(_file.read())
    return frames

def load_frame_from_file(filename):
    with open(filename, 'r') as fd:
        return fd.read()

async def sleep(tics=1):
    iteration_count = int(tics * 10)
    for _ in range(iteration_count):
        await asyncio.sleep(0)

async def show_gameover(canvas, window_height, window_width, frame):
    message_size_y, message_size_x = get_frame_size(frame)
    message_pos_y = round(window_height / 2) - round(message_size_y / 2)
    message_pos_x = round(window_width / 2) - round(message_size_x / 2)
    while True:
        draw_frame(canvas, message_pos_y, message_pos_x, frame)
        await asyncio.sleep(0)

async def count_years(year_counter, level_duration_sec=5):
    while True:
        await sleep(level_duration_sec)
        year_counter[0] += 1


async def show_year_counter(canvas, year_counter, start_year):
    canvas_height, canvas_width = canvas.getmaxyx()

    counter_lenght = 9
    year_str_pos_y = 1
    year_str_pos_x = round(canvas_width / 2) - round(counter_lenght / 2)

    while True:
        current_year = start_year + year_counter[0]
        canvas.addstr(
            year_str_pos_y,
            year_str_pos_x,
            f'Year {current_year}'
        )
        await asyncio.sleep(0)

async def blink(canvas, row, column, symbol='*'):

    state = random.randint(0,3)
    while True:
        if state == 0:
            canvas.addstr(row, column, symbol, curses.A_DIM)
            await sleep(2)
            state += 1

        if state == 1:
            canvas.addstr(row, column, symbol)
            await sleep(0.3)
            state += 1

        if state == 2:
            canvas.addstr(row, column, symbol, curses.A_BOLD)
            await sleep(0.5)
            state += 1

        if state == 3:
            canvas.addstr(row, column, symbol)
            await sleep(0.3)
            state = 0

async def animate_spaceship(canvas, frames, frame_container):
    frames_cycle = itertools.cycle(frames)

    while True:
        frame_container.clear()
        spaceship_frame = next(frames_cycle)
        frame_container.append(spaceship_frame)
        await asyncio.sleep(0)

async def run_spaceship(canvas, coros, start_row, start_column, frame_container, level, start_year):

    height, width = canvas.getmaxyx()
    border_size = 1

    frame_size_y, frame_size_x = get_frame_size(frame_container[0])
    frame_pos_x = round(start_column) - round(frame_size_x / 2)
    frame_pos_y = round(start_row) - round(frame_size_y / 2)

    row_speed, column_speed = 0, 0

    while True:

        direction_y, direction_x, spacebar = read_controls(canvas)

        current_year = start_year + level[0]
        if spacebar and current_year>=2020:
            shot_pos_x = frame_pos_x + round(frame_size_x / 2)
            shot_pos_y = frame_pos_y - 0
            shot_coro = fire(canvas, shot_pos_y, shot_pos_x)
            coros.append(shot_coro)

        row_speed, column_speed = update_speed(
            row_speed,
            column_speed,
            direction_y,
            direction_x
        )

        frame_pos_x += column_speed
        frame_pos_y += row_speed

        frame_x_max = frame_pos_x + frame_size_x
        frame_y_max = frame_pos_y + frame_size_y
        field_x_max = width - border_size
        field_y_max = height - border_size
        frame_pos_x = min(frame_x_max, field_x_max) - frame_size_x
        frame_pos_y = min(frame_y_max, field_y_max) - frame_size_y
        frame_pos_x = max(frame_pos_x, border_size)
        frame_pos_y = max(frame_pos_y, border_size)

        current_frame = frame_container[0]
        draw_frame(canvas, frame_pos_y, frame_pos_x, current_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, frame_pos_y, frame_pos_x, current_frame, negative=True)

        for obstacle in obstacles_actual:
            if obstacle.has_collision(frame_pos_y, frame_pos_x):
                game_over_coro = show_gameover(
                    canvas,
                    height,
                    width,
                    load_frame_from_file('game_over/game_over.txt')
                )
                coros.append(game_over_coro)
                return

async def fill_orbit_with_garbage(canvas, coros, garbage_frames, level,
        initial_timeout=5, complexity_factor=5, timeout_min=0.3):

    _, columns_number = canvas.getmaxyx()
    border_size = 1
    while True:
        current_trash_frame = random.choice(garbage_frames)
        _, trash_column_size = get_frame_size(current_trash_frame)
        random_column = random.randint(
            border_size,
            columns_number - border_size
        )
        actual_column = min(
            columns_number - trash_column_size - border_size,
            random_column + trash_column_size - border_size,
        )

        trash_coro = fly_garbage(canvas, actual_column, current_trash_frame)
        coros.append(trash_coro)
        timeout_step = level[0] / complexity_factor
        garbage_respawn_timeout = initial_timeout - timeout_step

        if garbage_respawn_timeout <= timeout_min:
            garbage_respawn_timeout = timeout_min
        await sleep(garbage_respawn_timeout)

def star_generator(height, width, number=300):

    for star in range(number):
        y_pos = random.randint(1, height - 2)
        x_pos = random.randint(1, width - 2)
        symbol = random.choice(SYMBOLS)

        yield y_pos, x_pos, symbol

def main(canvas):
    frame_container = []
    level = [0]
    start_year = 1957
    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)

    height, width = canvas.getmaxyx()
    status_bar_height = 2
    sb_begin_y = sb_begin_x = 0
    status_bar = canvas.derwin(
        status_bar_height,
        height,
        sb_begin_y,
        sb_begin_x
    )

    coroutines = [blink(canvas, row, column, symbol) for row, column, symbol in star_generator(height, width)]

    x_start = width / 2
    y_start = height / 2

    rocket_frames = get_frames_from_dir('animation_frames')
    garbage_frames = get_frames_from_dir('garbage')

    rocket_anim_coro = animate_spaceship(canvas, rocket_frames, frame_container)
    rocket_control_coro = run_spaceship(canvas, coroutines, y_start, x_start, frame_container, level, start_year)


    count_years_coro = count_years(level)
    show_year_counter_coro = show_year_counter(status_bar, level, start_year)

    coroutines.append(rocket_anim_coro)
    coroutines.append(rocket_control_coro)
    coroutines.append(fill_orbit_with_garbage(canvas, coroutines, garbage_frames, level))
    coroutines.append(count_years_coro)
    coroutines.append(show_year_counter_coro)


    while len(coroutines):
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)

        canvas.refresh()
        time.sleep(TIC_TIMEOUT)

if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(main)

