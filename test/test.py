# handlers.py
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from db import set_session
import requests
from config import RAPIDAPI_KEY
from states import BookingState
import app.keyboards as keyboards

router = Router()

API_HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "booking-com15.p.rapidapi.com"
}

DESTINATION_URL = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"


@router.message(CommandStart())
async def welcome_handler(msg: types.Message):
    await msg.answer(
        "Welcome to Globetrotter 365!\n\nClick a button to continue.",
        reply_markup=keyboards.continue_or_exit
    )


@router.message(F.text == "Continue")
async def handle_continue(msg: types.Message, state: FSMContext):
    await msg.answer("Please enter your destination:\n\n`City, Country`", parse_mode="Markdown")
    await state.set_state(BookingState.waiting_for_city_country)


@router.message(F.text == "Exit")
async def handle_exit(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("Goodbye!", reply_markup=ReplyKeyboardRemove())


@router.message(BookingState.waiting_for_city_country)
async def handle_city_country(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    parts = [part.strip() for part in msg.text.split(',', 1)]

    if len(parts) != 2:
        await msg.answer("✏️ Format must be `City, Country`", parse_mode="Markdown")
        return

    city, country = parts
    response = requests.get(DESTINATION_URL, headers=API_HEADERS, params={"query": city})
    data_list = response.json().get("data", [])
    matches = [loc for loc in data_list if
               city.lower() in loc.get("city_name", "").lower() and country.lower() in loc.get("country", "").lower()]

    if not matches:
        await msg.answer("❌ No matching locations found.")
        return

    set_session(user_id, "locations", matches)

    keyboard = [[KeyboardButton(text=loc.get("label", "Unknown"))] for loc in matches[:10]]
    keyboard.append([KeyboardButton(text="Not listed")])

    markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

    await msg.answer("📍 Please choose the correct location:", reply_markup=markup)
    await state.set_state(BookingState.waiting_for_location_selection)


@router.message(BookingState.waiting_for_location_selection)
async def handle_location_selection(msg: types.Message, state: FSMContext):
    chosen_label = msg.text
    await state.update_data(location_label=chosen_label)
    await msg.answer("📅 Please enter your check-in date (YYYY-MM-DD):")
    await state.set_state(BookingState.waiting_for_checkin_date)


@router.message(BookingState.waiting_for_checkin_date)
async def handle_checkin(msg: types.Message, state: FSMContext):
    checkin = msg.text.strip()
    # Optionally validate format here
    await state.update_data(checkin=checkin)
    await msg.answer("📅 Now enter your check-out date (YYYY-MM-DD):")
    await state.set_state(BookingState.waiting_for_checkout_date)


@router.message(BookingState.waiting_for_checkout_date)
async def handle_checkout(msg: types.Message, state: FSMContext):
    checkout = msg.text.strip()
    data = await state.get_data()

    checkin = data.get("checkin")
    location = data.get("location_label")

    await msg.answer(
        f"✅ Got it!\n\n"
        f"Location: {location}\n"
        f"Check-in: {checkin}\n"
        f"Check-out: {checkout}\n\n"
        f"Searching hotels..."
    )

    await state.clear()
    # Next: Search for hotels, present options...