import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage


bot = Bot(token="my_token")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


conn = sqlite3.connect('library.db')
cursor = conn.cursor()


cursor.execute('''
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title TEXT,
    author TEXT,
    description TEXT,
    genre TEXT
)
''')
conn.commit()

class BookStates:
    WaitingForTitle = "waiting_for_title"
    WaitingForAuthor = "waiting_for_author"
    WaitingForDescription = "waiting_for_description"
    WaitingForGenre = "waiting_for_genre"


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Добавить книгу", callback_data="add_book"))
    keyboard.add(InlineKeyboardButton(text="Просмотреть книги", callback_data="view_books"))
    keyboard.add(InlineKeyboardButton(text="Поиск книг", callback_data="search_books"))
    keyboard.add(InlineKeyboardButton(text="Удалить книгу", callback_data="delete_book"))
    await message.answer("Выберите действие:", reply_markup=keyboard)

# Handlers for collecting book details
@dp.callback_query_handler(lambda c: c.data == 'add_book')
async def add_book(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите название книги:")
    await state.set_state(BookStates.WaitingForTitle)


@dp.message_handler(state=BookStates.WaitingForTitle)
async def process_title(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['title'] = message.text
    await message.answer("Введите автора книги:")
    await state.set_state(BookStates.WaitingForAuthor)

@dp.message_handler(state=BookStates.WaitingForAuthor)
async def process_author(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['author'] = message.text
    await message.answer("Введите описание книги:")
    await state.set_state(BookStates.WaitingForDescription)

@dp.message_handler(state=BookStates.WaitingForDescription)
async def process_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await message.answer("Введите жанр книги (либо введите новый жанр):")
    await state.set_state(BookStates.WaitingForGenre)

@dp.message_handler(state=BookStates.WaitingForGenre)
async def process_genre(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['genre'] = message.text
    await save_book(message, state)

async def save_book(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        title = data['title']
        author = data['author']
        description = data['description']
        genre = data['genre']

    cursor.execute("INSERT INTO books (title, author, description, genre) VALUES (?, ?, ?, ?)", (title, author, description, genre))
    conn.commit()
    await message.answer("Книга успешно добавлена")

@dp.callback_query_handler(lambda c: c.data == 'view_books')
async def view_books(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    cursor.execute("SELECT title, author, description, genre FROM books")
    books = cursor.fetchall()
    if not books:
        await bot.send_message(callback_query.from_user.id, "Список книг пуст")
    else:
        keyboard = InlineKeyboardMarkup()
        for i, book in enumerate(books):
            button_text = f"{book[0]} - {book[1]}"
            button_data = f"view_book_{i}"
            keyboard.add(InlineKeyboardButton(text=button_text, callback_data=button_data))
        await bot.send_message(callback_query.from_user.id, "Выберите книгу для просмотра подробной информации:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data.startswith('view_book_'))
async def view_book(callback_query: types.CallbackQuery):
    book_index = int(callback_query.data.split('_')[-1])
    cursor.execute("SELECT title, author, description, genre FROM books")
    books = cursor.fetchall()
    book = books[book_index]
    book_info = f"Название: {book[0]}\nАвтор: {book[1]}\nОписание: {book[2]}\nЖанр: {book[3]}"
    await bot.send_message(callback_query.from_user.id, book_info)

@dp.callback_query_handler(lambda c: c.data == 'search_books')
async def search_books(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите ключевое слово для поиска:")


@dp.message_handler(state=BookStates.WaitingForGenre)
async def process_genre(message: types.Message, state: FSMContext):
    keyword = message.text
    cursor.execute("SELECT title, author, genre FROM books WHERE title LIKE ? OR author LIKE ? OR genre LIKE ?", ('%'+keyword+'%', '%'+keyword+'%', '%'+keyword+'%'))
    books = cursor.fetchall()
    if not books:
        await message.answer("Книги по вашему запросу не найдены")
    else:
        keyboard = InlineKeyboardMarkup()
        for i, book in enumerate(books):
            callback_data = f"show_book_{i+1}"
            keyboard.add(InlineKeyboardButton(text=f"{i+1}. {book[0]} - {book[1]} ({book[2]})", callback_data=callback_data))
        await message.answer("Результаты поиска:", reply_markup=keyboard)

dp.register_message_handler(process_genre, state=BookStates.WaitingForGenre)


@dp.callback_query_handler(lambda c: c.data.startswith('show_book_'))
async def show_book_info(callback_query: types.CallbackQuery):
    index = int(callback_query.data.split('_')[1]) - 1
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    if index < len(books):
        book = books[index]
        book_info = f"Название: {book[1]}\nАвтор: {book[2]}\nОписание: {book[3]}\nЖанр: {book[4]}"
        await bot.send_message(callback_query.from_user.id, book_info)
    else:
        await bot.send_message(callback_query.from_user.id, "Книга не найдена")

@dp.callback_query_handler(lambda c: c.data == 'delete_book')
async def delete_book(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Выберите книгу для удаления:")
    cursor.execute("SELECT id, title FROM books")
    books = cursor.fetchall()
    keyboard = InlineKeyboardMarkup()
    for book in books:
        keyboard.add(InlineKeyboardButton(text=book[1], callback_data=f"confirm_delete_book:{book[0]}"))
    await bot.send_message(callback_query.from_user.id, "Выберите книгу для удаления:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_delete_book'))
async def process_confirm_delete_book(callback_query: types.CallbackQuery):
    book_id = int(callback_query.data.split(":")[1])
    cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    await bot.answer_callback_query(callback_query.id, "Книга успешно удалена")

# Start polling
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
