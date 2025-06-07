from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    waiting_for_city_country = State()
    waiting_for_city_selection = State()
    waiting_for_checkin_date = State()
    waiting_for_checkout_date = State()
    waiting_for_adults_number = State()
    waiting_for_children_number = State()
    waiting_for_room_count = State()
    fetching_results_from_server = State()
    handling_next_step = State()
    setting_max_price = State()
    checking_nearby_locations = State()
    selecting_nearby_location = State()
    choosing_hotel = State()
    sending_reservation_link = State()