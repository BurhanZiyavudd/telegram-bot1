from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


continue_or_exit = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Continue"), KeyboardButton(text="Exit")]
],
    resize_keyboard=True,
    one_time_keyboard=True

)

adults_number = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3")],
    [KeyboardButton(text="4"), KeyboardButton(text="5"), KeyboardButton(text="6")]
],
    resize_keyboard=True,
    one_time_keyboard=True
)

children_number = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3")],
    [KeyboardButton(text="4"), KeyboardButton(text="5")]
],
    resize_keyboard=True,
    one_time_keyboard=True
)

room_count = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="One(1)"), KeyboardButton(text="Two(2)"), KeyboardButton(text="Three(3)")],
    [KeyboardButton(text="Four(4)")],
],
    resize_keyboard=True,
    one_time_keyboard=True
)

additional_functions = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Set Price Limit"), KeyboardButton(text="Check Nearby Locations")],
    [KeyboardButton(text="Reserve Room"), KeyboardButton(text="Another search/Start Over")],
    [KeyboardButton(text="Stop Session")],
],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Additional Functions:"
)