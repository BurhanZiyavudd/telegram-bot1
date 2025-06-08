import asyncio
import logging
import webbrowser
from aiogram.fsm.context import FSMContext
from hotel_app.states import HotelBookingState
from config import RAPIDAPI_KEY
from aiogram import types, Router, F
from aiogram.types import KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from db import *
import time
import requests
from requests.exceptions import Timeout, RequestException
import hotel_app.keyboards as keyboards
from datetime import datetime


router = Router()

logger = logging.getLogger(__name__)

headers = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": "booking-com15.p.rapidapi.com"
}


@router.message(CommandStart())
async def welcome(msg: types.Message):
    await msg.answer(
        "Welcome to Globetrotter 365!"
        "\n\nI'll assist you to seek the best, meanwhile the cheapest flight options and top-ranked hotels around the globe. "
        "Please inform if you want to proceed working with me."
        "\n\nClick on relevant button.",
        reply_markup=keyboards.continue_or_exit
    )

@router.message(F.text == "Continue")
async def handle_continue(msg: types.Message, state: FSMContext):
    await msg.answer("Please enter your destination:\n\n`City, Country`", parse_mode="Markdown")
    await state.set_state(HotelBookingState.waiting_for_city_country)

@router.message(F.text == "Exit")
async def handle_exit(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("Thank you for using Globetrotter 365!\nGoodbye!", parse_mode="Markdown", ReplyKeyboardRemove=True)


@router.message(HotelBookingState.waiting_for_city_country)
async def handle_waiting_for_country(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    parts = [part.strip() for part in msg.text.split(',', 1)]

    if len(parts) != 2:
        await msg.answer("\u270f\ufe0f Please enter a city and country in this format:\n\n`City, Country` (e.g., Moscow, Russia)", parse_mode="Markdown")
        return

    user_input_city, user_input_country = parts
    try:
        url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
        querystring = {"query": user_input_city}
        response = requests.get(url, headers=headers, params=querystring)

        if response.status_code != 200:
            await msg.answer(f"\u274c API Error: {response.status_code}")
            return

        result = response.json()
        logger.info("API result: %s", result)

        data_list = result.get("data", [])
        matches = [
            loc for loc in data_list
            if user_input_city.lower() in loc.get("city_name", "").lower()
            and user_input_country.lower() in loc.get("country", "").lower()
        ]

        if not matches:
            await msg.answer("\u274c No matching locations found.")
            return

        set_session(user_id, "locations", matches)

        keyboard = [[KeyboardButton(text=loc.get("label", "Unknown"))] for loc in matches[:10]]
        keyboard.append([KeyboardButton(text="Not listed")])

        markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await msg.answer("\U0001F4CD Please choose the correct location:", reply_markup=markup)
        await state.set_state(HotelBookingState.waiting_for_city_selection)

    except Timeout:
        await msg.answer("\u23f1\ufe0f The server took too long to respond. Please try again.")

    except Exception as e:
        await msg.answer(f"\u26a0\ufe0f Unexpected error: {str(e)}")

@router.message(HotelBookingState.waiting_for_city_selection)
async def handle_waiting_for_city(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    if msg.text == "Not listed":
        locations = get_session(user_id).get("locations", [])
        if len(locations[10:]) > 0:
            keyboard = [[KeyboardButton(text=loc.get("label", "Unknown"))] for loc in get_session("locations")[10:20]]

            markup = types.ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )

            await msg.answer(f"\u274c You might had in view on of these locations...", parse_mode="Markdown", reply_markup=markup)
            return await state.set_state(HotelBookingState.waiting_for_city_selection)
        else:
            await msg.answer("No locations found with this name. Please try to enter the names or consider the nearby destinations...", parse_mode="Markdown")
            return await state.set_state(HotelBookingState.waiting_for_city_country)
    else:
        for loc in get_session(user_id).get("locations", []):
            label = loc.get("label", "").strip().lower()
            if label == msg.text.strip().lower():

                set_session(user_id, "city_name", loc.get("city_name", ""))
                set_session(user_id, "country", loc.get("country", ""))
                set_session(user_id, "location_photo", loc.get("image_url", ""))
                set_session(user_id, "latitude", loc.get("latitude", ""))
                set_session(user_id, "longitude", loc.get("longitude", ""))
                set_session(user_id, "dest_id", loc.get("dest_id", ""))
                set_session(user_id, "search_type", loc.get("search_type", "").upper())
                break

        chosen_label = msg.text
        await state.update_data(location_label=chosen_label)
        await msg.answer("📅 Please indicate your check-in date in DD/MM/YYYY format:")
        await state.set_state(HotelBookingState.waiting_for_checkin_date)

@router.message(HotelBookingState.waiting_for_checkin_date)
async def handle_waiting_for_checkin(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    try:
        input_checkin_date = msg.text
        await state.update_data(checkin_date=input_checkin_date)
        formatted_checkin = datetime.strptime(input_checkin_date, "%d/%m/%Y").strftime("%Y-%m-%d")
        set_session(user_id, "checkin", formatted_checkin)
        await msg.answer("📅 Now enter your check-out date in DD/MM/YYYY format:")
        await state.set_state(HotelBookingState.waiting_for_checkout_date)
    except ValueError:
        await msg.answer("\u274c Invalid date format. Please try again.")
        return await state.set_state(HotelBookingState.waiting_for_checkin_date)

@router.message(HotelBookingState.waiting_for_checkout_date)
async def handle_waiting_for_checkout(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    try:
        input_checkout_date = msg.text
        await state.update_data(checkout_date=input_checkout_date)
        formatted_checkout = datetime.strptime(input_checkout_date, "%d/%m/%Y").strftime("%Y-%m-%d")
        set_session(user_id, "checkout", formatted_checkout)
        await msg.answer(
            "Clarify a number of adults below (Age above 18 y.o.)...",
                         parse_mode="Markdown",
                         reply_markup=keyboards.adults_number
            )
        await state.set_state(HotelBookingState.waiting_for_adults_number)
    except ValueError:
        await msg.answer("\u274c Invalid date format. Please try again.")
        return await state.set_state(HotelBookingState.waiting_for_checkout_date)

@router.message(HotelBookingState.waiting_for_adults_number)
async def handle_waiting_for_adults(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    input_adults = msg.text.strip()

    if input_adults.isdigit() and 1<=int(input_adults)<=6:

        keyboard = [[KeyboardButton(text="Yes"), KeyboardButton(text="No")]]

        markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard =True,
            one_time_keyboard=True
        )

        await state.update_data(adults=input_adults)
        set_session(user_id, "adults", input_adults)
        await msg.answer(f"✅ Got it. {input_adults} adult(s)\n\nAre there any children who's age is under 18 years old with you?", reply_markup=markup)
        await state.set_state(HotelBookingState.waiting_for_children_number)

    else:
        await msg.answer("Please enter a valid adults number.")
        return await state.set_state(HotelBookingState.waiting_for_adults_number)

@router.message(HotelBookingState.waiting_for_children_number)
async def handle_waiting_for_children(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    user_choice = msg.text.strip().lower()
    data = await state.get_data()

    if user_choice in ("yes", "no"):
        await state.update_data(children_answered=user_choice)

        if user_choice == "yes":
            await msg.answer("🧒 How many children (under 18 y.o) will stay?", reply_markup=keyboards.children_number)
        else:
            set_session(user_id, "children", "0")
            await msg.answer("🛏️ How many rooms do you need?", reply_markup=keyboards.room_count)
            await state.set_state(HotelBookingState.waiting_for_room_count)
        return

    if data.get("children_answered") == "yes":
        if not user_choice.isdigit() or int(user_choice) < 1:
            await msg.answer("❌ Please enter a valid number of children (must be at least 1).")
            return

        await state.update_data(children_number=int(user_choice))
        await msg.answer("📊 Please enter the ages of the children separated by commas (e.g., 5, 8, 12).")
        await state.set_state(HotelBookingState.waiting_for_children_ages)
        return

    # Fallback
    await msg.answer("❓ Please select 'Yes' or 'No', or enter the number of children.")

@router.message(HotelBookingState.waiting_for_children_ages)
async def handle_children_ages(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    ages_text = msg.text.strip()
    data = await state.get_data()
    expected_number = data.get("children_number", 0)

    try:
        ages = [int(age.strip()) for age in ages_text.split(",") if age.strip()]
    except ValueError:
        await msg.answer("❌ Please enter only numbers separated by commas.")
        return

    if len(ages) != expected_number:
        await msg.answer(f"❌ You said there are {expected_number} children, but you provided {len(ages)} ages. Please try again.")
        return

    if any(age >= 18 or age < 0 for age in ages):
        await msg.answer("❌ All children's ages must be between 0 and 17.")
        return

    set_session(user_id, "children", ",".join(map(str, ages)))

    await msg.answer("🛏️ How many rooms do you need?", reply_markup=keyboards.room_count)
    await state.set_state(HotelBookingState.waiting_for_room_count)

@router.message(HotelBookingState.waiting_for_room_count)
async def handle_waiting_for_room_count(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    room_count = msg.text.strip()[-2]
    set_session(user_id, "room", room_count)
    await state.update_data(room_count=room_count)
    await msg.answer("Starting checking for available hotels...")
    await handle_fetching_results(msg, state)

@router.message(HotelBookingState.fetching_results_from_server)
async def handle_fetching_results(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id

    user_data = get_session(user_id)

    found_hotels_dict = {}

    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
    querystring = {
        "dest_id": user_data["dest_id"],
        "search_type": user_data["search_type"],
        "arrival_date": user_data["checkin"],
        "departure_date": user_data["checkout"],
        "adults": user_data["adults"],
        "children_age": user_data.get("children", ""),
        "room_qty": user_data["room"],
        "price_min": "0",
        "price_max": user_data.get("max_price", ""),
        "page_number": "1",
        "languagecode": "en-us",
        "currency_code": "USD"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        try:
            response_data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse hotel JSON: {e} - Raw response: {response.text}")
            await msg.answer("⚠️ Failed to parse hotel data.")
            return

        hotels_list = response_data.get("data", {}).get("hotels", [])

        if not isinstance(hotels_list, list) or not hotels_list:
            logger.warning(f"Empty or invalid hotel list: {hotels_list}")
            await msg.answer("❌ No hotels found or the response was invalid.")
            return
        for hotel in hotels_list[:12]:
            hotel_id = hotel.get("hotel_id", "unknown")

            url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelDetails"

            querystring = {
                "hotel_id": hotel_id,
                "arrival_date": user_data["checkin"],
                "departure_date": user_data["checkout"],
                "adults": user_data["adults"],
                "children_age": user_data.get("children", ""),
                "room_qty": user_data["room"],
                "page_number": "1",
                "languagecode": "en-us",
                "currency_code": "USD"
            }

            price_per_night = "N/A"
            price_total = "N/A"

            try:
                response1 = requests.get(url, headers=headers, params=querystring, timeout=10)
                if response1.status_code == 200:
                    price_per_night = response1.json().get("data", {}).get("product_price_breakdown", {}).get(
                        "gross_amount_per_night", {}).get("amount_rounded", "N/A")
                    price_total = response1.json().get("data", {}).get("product_price_breakdown", {}).get(
                        "all_inclusive_amount", {}).get("amount_rounded", "N/A")

            except Exception as e:
                logging.error(e)

            name = hotel.get("property", {}).get("name", "N/A")
            price = hotel.get("property", {}).get("priceBreakdown", {}).get("grossPrice", {}).get("value", "N/A")
            currency = hotel.get("property", {}).get("priceBreakdown", {}).get("grossPrice", {}).get("currency", "")
            rating = hotel.get("property", {}).get("reviewScore", "N/A")
            description = hotel.get("accessibilityLabel", "")
            session = get_session(user_id)

            found_hotels_dict[hotel_id] = name

            descs = session.get("hotel_descriptions")
            if not isinstance(descs, dict):
                descs = {}

            descs[hotel_id] = description

            set_session(user_id, "hotel_descriptions", descs)

            photos = hotel.get("property", {}).get("photoUrls", [])

            photo_urls = [url for url in photos if isinstance(url, str) and ".jpg" in url]
            photo_url = photo_urls[0] if photo_urls else None

            caption = (
                f"🏨 <b>{name}</b>\n"
                f"💰 Price: {round(price, 2)} {currency} (taxes and fees included)\n"
                f"      Price per night: {price_per_night}\n"
                f"      Price in total: {price_total}\n"
                f"⭐ Rating: {rating}\n"
                f"To get more info please click on button below ⬇️"
            )

            callback = f"moreinfo_{hotel_id}"
            inline_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="More Info 📝", callback_data=callback)],
                ]
            )

            try:
                if photo_url:
                    await msg.answer_photo(photo=photo_url, caption=caption, parse_mode="html", reply_markup=inline_keyboard)
                else:
                    await msg.answer(caption, parse_mode="html", reply_markup=inline_keyboard)
            except Exception as e:
                logging.error(f"[Photo send failed] {e}")
                await msg.answer(caption, parse_mode="html", reply_markup=inline_keyboard)

            set_session(user_id, "hotels_dict", found_hotels_dict)

        await msg.answer(
            "Please clarify the next step by clicking on relevant button below.",
            reply_markup=keyboards.additional_functions
        )
        await state.set_state(HotelBookingState.handling_next_step)

    except RequestException as e:
        logging.error(e)
        await msg.answer("API Error. Please try again later.")
    except Exception as e:
        logging.error(e)
        await msg.answer(f"Request failed: {e}")

@router.callback_query()
async def moreinfo_callback(call: CallbackQuery):
    user_id = call.from_user.id
    hotel_id = call.data.split("_")[1]

    await call.answer()

    descs = get_session(user_id).get("hotel_descriptions", {})
    description = descs.get(hotel_id, "No additional info available.")

    # Get hotel photo URLs
    photo_url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelPhotos"
    detail_url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelDetails"

    photo_query = {"hotel_id": hotel_id}
    detail_query = {
        "hotel_id": hotel_id,
        "arrival_date": get_session(user_id).get("checkin"),
        "departure_date": get_session(user_id).get("checkout"),
        "adults": get_session(user_id).get("adults"),
        "children_age": get_session(user_id).get("children"),
        "room_qty": get_session(user_id).get("room"),
        "units": "metric",
        "temperature_unit": "c",
        "languagecode": "en-us",
        "currency_code": "USD"
    }

    try:
        response = requests.get(photo_url, headers=headers, params=photo_query, timeout=10)

        if response.status_code == 200:
            hotel_images = response.json().get("data", [])
            hotel_photos = [img.get("url") for img in hotel_images if img.get("url") and ".jpg" in img.get("url")]

            if not hotel_photos:
                await call.message.answer("⚠️ No photos found for this hotel.")
                return

            max_photos = 15
            hotel_photos = hotel_photos[:max_photos]

            for i, photo_url in enumerate(hotel_photos):
                try:
                    if i == len(hotel_photos) - 1:
                        await call.message.answer_photo(
                            photo=photo_url,
                            caption=f"📌 <b>Additional Info:</b>\n{description}",
                            parse_mode="HTML"
                        )
                    else:
                        await call.message.answer_photo(photo=photo_url)
                        await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"[Photo send failed] {e}")
                    if i == len(hotel_photos) - 1:
                        await call.message.answer(f"📌 <b>Additional Info:</b>\n{description}", parse_mode="HTML")
        else:
            await call.message.answer("⚠️ API error. Couldn't retrieve photos.")
    except Exception as e:
        await call.message.answer(f"⚠️ Failed to fetch images: {e}")

@router.message(HotelBookingState.handling_next_step)
async def handling_next_step(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id

    if msg.text == "Set Price Limit":
        await msg.answer("Please enter the maximum price that you are considering "
                         "(just the number, like `1000`. Amount will be accounted in USD)...", parse_mode="Markdown")
        await state.set_state(HotelBookingState.setting_max_price)

    elif msg.text == "Check Nearby Locations":
        await msg.answer("🔍 Searching for nearby cities...")
        await state.set_state(HotelBookingState.checking_nearby_locations)
        await checking_nearby_locations(msg, state)

    elif msg.text == "Reserve Room":
        await msg.answer("Great! Proceeding to reservation...")
        await state.set_state(HotelBookingState.choosing_hotel)
        await choosing_hotel(msg, state)

    elif msg.text == "Another Search/Start Over":
        clear_session(user_id)
        await state.clear()
        await msg.answer("🔄 Starting a new search from the beginning...\nPlease enter your destination:\n\n`City, Country`", parse_mode="Markdown")
        await state.set_state(HotelBookingState.waiting_for_city_country)
        await handle_waiting_for_country(msg, state)

    elif msg.text == "Stop Session":
        clear_session(user_id)
        await state.clear()
        await msg.answer("👋 Session ended. Come back any time!")

@router.message(HotelBookingState.setting_max_price)
async def setting_max_price(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    max_price = msg.text.strip()

    if max_price.isdigit():
        set_session(user_id, "max_price", max_price)
        await handle_fetching_results(msg, state)
    else:
        await msg.answer("❌ Please enter digits only (no letters or special characters).")
        await state.set_state(HotelBookingState.setting_max_price)

@router.message(HotelBookingState.checking_nearby_locations)
async def checking_nearby_locations(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id

    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getNearbyCities"
    querystring = {
        "latitude": get_session(user_id).get("latitude"),
        "longitude": get_session(user_id).get("longitude"),
        "languagecode": "en-us"
    }

    try:
        response = requests.get(url=url, headers=headers, params=querystring, timeout=10)

        if response.status_code != 200:
            await msg.answer(f"❌ API Error: {response.status_code}")
            return

        result = response.json()
        locations = result.get("data", [])
        if not locations:
            await msg.answer("⚠️ No nearby cities found.")
            return

        set_session(user_id, "locations", locations)

        keyboard = [
            [KeyboardButton(text=location.get("name", "N/A"))] for location in locations[:10]
        ]

        markup = types.ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await msg.answer("📍 Please choose a nearby city:", reply_markup=markup)
        await state.set_state(HotelBookingState.selecting_nearby_location)

    except Exception as e:
        logger.error(f"[Nearby City Error] {e}")
        await msg.answer(f"🚫 Could not retrieve nearby cities.\n\nError: {e}")

@router.message(HotelBookingState.selecting_nearby_location)
async def selecting_nearby_location(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    selected_location = msg.text.strip().lower()

    locations = get_session(user_id).get("locations", [])

    for loc in locations:
        label = loc.get("name", "").strip().lower()
        if label == selected_location:
            set_session(user_id, "city_name", loc.get("name", ""))
            set_session(user_id, "latitude", loc.get("latitude", ""))
            set_session(user_id, "longitude", loc.get("longitude", ""))
            set_session(user_id, "dest_id", loc.get("dest_id", ""))
            set_session(user_id, "search_type", loc.get("dest_type", "").upper())

            await msg.answer(f"✅ New location selected. Searching hotels in {selected_location}...")
            await handle_fetching_results(msg, state)
            return
    await msg.answer("⚠️ Invalid selection. Please select a location from the list again.")

@router.message(HotelBookingState.choosing_hotel)
async def choosing_hotel(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    hotels_dict = get_session(user_id).get("hotels_dict", {})

    keyboard = []
    for hotel_id, hotel_name in hotels_dict.items():
        if isinstance(hotel_name, str):
            keyboard.append([KeyboardButton(text=hotel_name)])

    if not keyboard:
        await msg.answer("⚠️ No valid hotels to show.")
        return

    markup = types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await msg.answer("Please choose one of the hotels presented below:", reply_markup=markup)
    await state.set_state(HotelBookingState.sending_reservation_link)

@router.message(HotelBookingState.sending_reservation_link)
async def sending_reservation_link(msg: types.Message, state: FSMContext):
    user_id = msg.from_user.id
    chosen_hotel_name = msg.text.strip()
    hotels_dict = get_session(user_id).get("hotels_dict", {})

    chosen_hotel_id = ""
    for hotel_id, hotel_name in hotels_dict.items():
        if hotel_name.strip().lower() == chosen_hotel_name.lower():
            chosen_hotel_id = hotel_id
            break

    if not chosen_hotel_id:
        await msg.answer("❌ Could not recognize the hotel you selected. Please try again.")
        print(f"[DEBUG] User input hotel not found: {chosen_hotel_name}")
        return

    set_session(user_id, "chosen_hotel_id", chosen_hotel_id)

    url = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelDetails"
    querystring = {
        "hotel_id": chosen_hotel_id,
        "arrival_date": get_session(user_id).get("checkin"),
        "departure_date": get_session(user_id).get("checkout"),
        "adults": get_session(user_id).get("adults"),
        "children_age": get_session(user_id).get("children"),
        "room_qty": get_session(user_id).get("room"),
        "units": "metric",
        "temperature_unit": "c",
        "languagecode": "en-us",
        "currency_code": "USD"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        if response.status_code == 200:
            booking_url = response.json().get("data", {}).get("url", None)
            if booking_url:
                await msg.answer("🔗Wait a bit! You will be redirected to the official room reservation page of booking.com.", parse_mode="HTML")
                time.sleep(3)
                webbrowser.open_new_tab(booking_url)
                await msg.answer(f"Here’s your reservation link:\n{booking_url}")
            else:
                await msg.answer("⚠️ No reservation link found.")
        else:
            await msg.answer(f"⚠️ API error: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"[Reservation Link Error] {e}")
        await msg.answer(f"An error occurred while fetching reservation link:\n{e}")

@router.message()
async def fallback(msg: types.Message):
    await msg.answer("❓ I didn't understand that. Please select from the options.")
    print(f"[UNHANDLED MESSAGE] {msg.text}")