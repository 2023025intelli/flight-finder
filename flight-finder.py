#! ./venv/bin/python
from datetime import datetime, timedelta
import argparse
import aiohttp
import asyncio


async def main():
    args = parse_args()
    if args:
        from_city_code = await get_city_code(args['city_from'])
        if from_city_code is None:
            print(f'\x1b[1;31m City code for {args["city_from"]} not found \x1b[0m')
            return
        to_city_code = await get_city_code(args['city_to'])
        if to_city_code is None:
            print(f'\x1b[1;31m City code for {args["city_to"]} not found \x1b[0m')
            return
        airlines = await get_airline_codes()
        flights = await get_flights(from_city_code, to_city_code, args)
        if flights is None:
            print(f'\x1b[1m No flights found \x1b[0m')
            return
        for flight in flights:
            flight_detail_str = f' {flight["cityFrom"]} -> {flight["cityTo"]} | {flight["price"]} | {(flight["seats"])} seats left | Flight duration ({flight["duration"]}) '
            flight_detail = f'\x1b[1;33m|\x1b[0m\x1b[1m {flight["cityFrom"]}\x1b[0m \x1b[1;32m->\x1b[0m \x1b[1m{flight["cityTo"]}\x1b[0m \x1b[1;32m|\x1b[0m ' \
                            f'\x1b[1m{flight["price"]}$\x1b[0m \x1b[1;32m|\x1b[0m \x1b[1m{(flight["seats"])} seats left\x1b[0m ' \
                            f'\x1b[1;32m|\x1b[0m \x1b[1mFlight duration ({flight["duration"]})\x1b[0m '
            if 'return_duration' in flight and flight['return_duration']:
                flight_detail_str += f'| Return duration ({flight["return_duration"]}) '
                flight_detail += f'\x1b[1;32m|\x1b[0m \x1b[1mReturn duration ({flight["return_duration"]})\x1b[0m '
            max_len = flight_detail_str.__len__()
            route_details = []
            for route in flight['routes']:
                airline = next((item['name'] for item in airlines if item['id'] == route['airline']), None)
                detail_len = f'     {route["cityFrom"]} -> {route["cityTo"]} | {airline} | Departure {route["dTime"].strftime("%a %d/%m/%Y %H:%M")} | Arrival {route["aTime"].strftime("%a %d/%m/%Y %H:%M")} '.__len__()
                if detail_len > max_len:
                    max_len = detail_len
                route_detail = {'str': f'\x1b[1;33m|\x1b[0m    \x1b[1m {route["cityFrom"]}\x1b[0m \x1b[1;32m->\x1b[0m \x1b[1m{route["cityTo"]}\x1b[0m \x1b[1;32m|\x1b[0m '
                               f'\x1b[1m{airline}\x1b[0m \x1b[1;32m|\x1b[0m \x1b[1mDeparture {route["dTime"].strftime("%a %d/%m/%Y %H:%M")}\x1b[0m '
                               f'\x1b[1;32m|\x1b[0m \x1b[1mArrival {route["aTime"].strftime("%a %d/%m/%Y %H:%M")}\x1b[0m ', 'len': detail_len}
                route_details.append(route_detail)
            print('\x1b[1;33m' + '-' * (max_len + 2) + '\x1b[0m')
            flight_detail += ' ' * (max_len - flight_detail_str.__len__() - 1) + '\x1b[1;33m|\x1b[0m'
            print(f'{flight_detail}')
            print('\x1b[1;33m' + '-' * (max_len + 2) + '\x1b[0m')
            for detail in route_details:
                detail['str'] += ' ' * (max_len - detail['len']) + '\x1b[1;33m|\x1b[0m'
                print(detail['str'])
            print('\x1b[1;33m' + '-' * (max_len + 2) + '\x1b[0m')
    else:
        print('\x1b[1;31m !!! Invalid options !!!\x1b[0m \n\x1b[1m Try \'./flight-finder --help\' for more detail \x1b[0m')
        return


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', '-o', help='The city of departure.', type=str)
    parser.add_argument('--destination', '-d', help='The destination city.', type=str)
    parser.add_argument('--date_from', '-f', help='Start of departure date range. default TODAY', type=lambda d: datetime.strptime(d, '%d/%m/%Y').date(), default=datetime.today())
    parser.add_argument('--date_to', '-t', help='End of departure date range. default TOMORROW', type=lambda d: datetime.strptime(d, '%d/%m/%Y').date())
    parser.add_argument('--return_from', help='Start of arrival date range.', type=lambda d: datetime.strptime(d, '%d/%m/%Y').date())
    parser.add_argument('--return_to', help='End of arrival date range.', type=lambda d: datetime.strptime(d, '%d/%m/%Y').date())
    parser.add_argument('--direct', help='Search for direct flights only. default False', action='store_true')
    parser.add_argument('--max_price', '-m', help='Maximum price of ticket.', type=int)
    parser.add_argument('--limit', '-l', help='Max number of search results. default 10', type=int, default=10)
    args = parser.parse_args()
    result = {}
    if args.origin and args.destination:
        result['city_from'] = args.origin
        result['city_to'] = args.destination
    else:
        return get_args()
    if args.date_from:
        result['date_from'] = args.date_from
        result['date_to'] = (args.date_from + timedelta(days=1))
    if args.date_to:
        result['date_to'] = args.date_to
        if not args.date_from:
            result['date_from'] = (args.date_to - timedelta(days=7))
    if args.return_from:
        result['return_from'] = args.return_from
        result['return_to'] = (args.return_from + timedelta(days=1))
    if args.return_to:
        result['return_to'] = args.return_to
        if not args.return_from:
            result['return_from'] = (args.return_to - timedelta(days=7))
    if args.max_price:
        result['max_price'] = args.max_price
    if args.direct:
        result['direct'] = args.direct
    else:
        result['direct'] = False
    if args.limit:
        result['limit'] = args.limit
    return result


def get_args():
    city_from = None
    city_to = None
    return_from = return_to = max_price = None
    while not city_from:
        city_from = input(' Enter the origin city: ')
    while not city_to:
        city_to = input(' Enter the destination city: ')
    idate_from = input(' Start departure date range (dd/mm/yyyy) (skippable): ')
    if idate_from:
        date_from = str_to_date(idate_from)
    else:
        date_from = datetime.today()
    date_to = (date_from + timedelta(days=1))
    idate_to = input(' End departure date range (dd/mm/yyyy) (skippable): ')
    if idate_to:
        date_to = str_to_date(idate_to)
        if not idate_from and date_to:
            date_from = (date_to - timedelta(days=7))
    ireturn_from = input(' Start return date range (dd/mm/yyyy) (skippable): ')
    if ireturn_from:
        return_from = str_to_date(ireturn_from)
        return_to = (return_from + timedelta(days=1))
    ireturn_to = input(' End return date range (dd/mm/yyyy) (skippable): ')
    if ireturn_to:
        return_to = str_to_date(ireturn_to)
        if not ireturn_from and return_to:
            return_from = (return_to - timedelta(days=7))
    imax_price = input(' Maximum price (USD) (skippable): ')
    if imax_price and imax_price.isnumeric():
        max_price = int(imax_price)
    idirect = input(' Is direct flights only (y/n) (skippable): ')
    if idirect:
        direct = str_to_bool(idirect)
    else:
        direct = False
    ilimit = input(' Max number of results (skippable): ')
    if ilimit and ilimit.isnumeric():
        limit = int(ilimit)
    else:
        limit = 10
    result = {'city_from': city_from, 'city_to': city_to, 'date_from': date_from, 'date_to': date_to, 'direct': direct, 'limit': limit}
    if max_price:
        result['max_price'] = max_price
    if return_from:
        result['return_from'] = return_from
    if return_to:
        result['return_to'] = return_to
    return result


async def get_city_code(city):
    URL = "https://api.skypicker.com/locations"
    PARAMS = {'locale': 'en-US', 'location_types': 'city', 'limit': 1, 'active_only': 'true', 'sort': 'name', 'term': city}
    async with aiohttp.ClientSession() as session:
        loading_task = asyncio.create_task(loader(f'Resolving city code for {city}...'))
        resp = await fetch(session, URL, PARAMS)
        loading_task.cancel()
        print(f'\x1b[1m Resolving city code for {city}... done \x1b[0m')
        if resp and 'locations' in resp and resp['locations']:
            data = resp['locations']
            if 'code' in data[0]:
                return data[0]['code']
        else:
            return None


async def get_flights(from_city, to_city, optional_params):
    date_from = optional_params['date_from'].strftime('%d/%m/%Y')
    date_to = optional_params['date_to'].strftime('%d/%m/%Y')
    limit = optional_params['limit']
    direct = 1 if optional_params['direct'] else 0
    URL = 'https://api.skypicker.com/flights'
    PARAMS = {'flyFrom': from_city, 'to': to_city, 'dateFrom': date_from, 'date_to': date_to, 'partner': 'picky', 'direct_flights': direct, 'limit': limit}
    if 'max_price' in optional_params:
        PARAMS['max_price'] = optional_params['max_price']
    if 'return_from' in optional_params:
        PARAMS['return_from'] = optional_params['return_from'].strftime('%d/%m/%Y')
    if 'return_to' in optional_params:
        PARAMS['return_to'] = optional_params['return_to'].strftime('%d/%m/%Y')
    async with aiohttp.ClientSession() as session:
        loading_task = asyncio.create_task(loader(f'Searching for affordable flight from {from_city} to {to_city}...'))
        resp = await fetch(session, URL, PARAMS)
        loading_task.cancel()
        print(f'\x1b[1m Searching for affordable flight from {from_city} to {to_city}... done \x1b[0m')
        if resp and 'data' in resp and len(resp['data']) > 0:
            flights = []
            for data in resp['data']:
                flight = {}
                flight['price'] = data['price']
                flight['cityFrom'] = data['cityFrom']
                flight['countryFrom'] = data['countryFrom']['name']
                flight['cityTo'] = data['cityTo']
                flight['countryTo'] = data['countryTo']['name']
                flight['duration'] = data['fly_duration']
                flight['return_duration'] = data['return_duration'] if 'return_duration' in data else None
                flight['distance'] = data['distance']
                flight['seats'] = data['availability']['seats'] or 0
                flight['routes'] = []
                routes = data['route']
                for route in routes:
                    item = {}
                    item['airline'] = route['airline']
                    item['dTime'] = datetime.fromtimestamp(route['dTime'])
                    item['aTime'] = datetime.fromtimestamp(route['aTime'])
                    item['cityFrom'] = route['cityFrom']
                    item['cityTo'] = route['cityTo']
                    item['flight_no'] = route['flight_no']
                    flight['routes'].append(item)
                flights.append(flight)
            return flights


async def get_airline_codes():
    async with aiohttp.ClientSession() as session:
        loading_task = asyncio.create_task(loader('Fetching airline codes...'))
        resp = await fetch(session, 'https://api.skypicker.com/airlines')
        loading_task.cancel()
        print(f'\x1b[1m Fetching airline codes... done \x1b[0m')
        return resp


async def fetch(session, url, params=None):
    async with session.get(url, params=params) as response:
        return await response.json()


async def loader(text):
    loading_chars = ['-', '\\', '|', '/']
    index = 0
    while True:
        loading_char = loading_chars[index % 4]
        print(f'\x1b[1;33m {text} {loading_char} \x1b[0m', end='\r')
        index += 1
        await asyncio.sleep(0.3)


def str_to_bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def str_to_date(v):
    try:
        date = datetime.strptime(v, '%d/%m/%Y').date()
        return date
    except:
        print('\x1b[1;31m Invalid date... \x1b[0')
        return None


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()

    # pending = asyncio.all_tasks()
    # loop.run_until_complete(asyncio.gather(*pending))

    # Cancel all pending tasks
    # pending = asyncio.Task.all_tasks()
    # for task in pending:
    #     task.cancel()
    #     with suppress(asyncio.CancelledError):
    #         loop.run_until_complete(task)

    input("Press the enter key to exit...")
