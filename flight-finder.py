#! ./venv/bin/python
from datetime import datetime, timedelta
import argparse
import aiohttp
import asyncio


async def main():
    args = parse_args()
    if args:
        from_city_code = await get_city_code(args['from'])
        if from_city_code is None:
            print(f'\x1b[1;31m City code for {args["from"]} not found \x1b[0m')
            return
        to_city_code = await get_city_code(args['to'])
        if to_city_code is None:
            print(f'\x1b[1;31m City code for {args["to"]} not found \x1b[0m')
            return
        airlines = await get_airline_codes()
        flights = await get_flights(from_city_code, to_city_code, args)
        if flights is None:
            print(f'\x1b[1m No flights found \x1b[0m')
            return
        for flight in flights:
            flight_detail = f'\x1b[1m {flight["cityFrom"]}\x1b[0m \x1b[1;32m->\x1b[0m \x1b[1m{flight["cityTo"]}\x1b[0m \x1b[1;32m|\x1b[0m ' \
                            f'\x1b[1m{flight["price"]}$\x1b[0m \x1b[1;32m|\x1b[0m \x1b[1m{(flight["seats"])} seats left\x1b[0m ' \
                            f'\x1b[1;32m|\x1b[0m \x1b[1mFlight duration ({flight["duration"]})\x1b[0m '
            if 'return_duration' in flight and flight['return_duration']:
                flight_detail += f'\x1b[1;32m|\x1b[0m \x1b[1mReturn duration ({flight["return_duration"]})\x1b[0m '
            route_details = []
            for route in flight['routes']:
                airline = next((item['name'] for item in airlines if item['id'] == route['airline']), None)
                route_detail = f'    \x1b[1m {route["cityFrom"]}\x1b[0m \x1b[1;32m->\x1b[0m \x1b[1m{route["cityTo"]}\x1b[0m \x1b[1;32m|\x1b[0m ' \
                               f'\x1b[1m{airline}\x1b[0m \x1b[1;32m|\x1b[0m \x1b[1mDeparture {route["dTime"].strftime("%a %d/%m/%Y %H:%M")}\x1b[0m ' \
                               f'\x1b[1;32m|\x1b[0m \x1b[1mArrival {route["aTime"].strftime("%a %d/%m/%Y %H:%M")}\x1b[0m \x1b[1;32m|\x1b[0m '
                route_details.append(route_detail)
            print(flight_detail)
            for detail in route_details:
                print(detail)
            print('\n')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', '-o', help='The city of departure.', type=str, required=True)
    parser.add_argument('--destination', '-d', help='The destination city.', type=str, required=True)
    parser.add_argument('--date_from', '-f', help='Start of departure date range. default TODAY', type=lambda d: datetime.strptime(d, '%d/%m/%Y').date(), default=datetime.today())
    parser.add_argument('--date_to', '-t', help='End of departure date range. default TOMORROW', type=lambda d: datetime.strptime(d, '%d/%m/%Y').date())
    parser.add_argument('--return_from', help='Start of arrival date range.', type=lambda d: datetime.strptime(d, '%d/%m/%Y').date())
    parser.add_argument('--return_to', help='End of arrival date range.', type=lambda d: datetime.strptime(d, '%d/%m/%Y').date())
    parser.add_argument('--direct', help='Search for direct flights only. default False', type=str_to_bool, default=False)
    parser.add_argument('--max_price', '-m', help='Maximum price of ticket.', type=int)
    parser.add_argument('--limit', '-l', help='Max number of search results. default 10', type=int, default=10)
    args = parser.parse_args()
    result = {}
    if args.origin and args.destination:
        result['from'] = args.origin
        result['to'] = args.destination
    else:
        print('\x1b[3;31m !!! Invalid options !!!\x1b[0m \n\x1b[1m Try \'./flight-finder --help\' for more detail \x1b[0m')
        return
    if args.limit:
        result['limit'] = args.limit
    if args.max_price:
        result['max_price'] = args.max_price
    if args.date_from:
        result['date_from'] = args.date_from
        result['date_to'] = (args.date_from + timedelta(days=1))
    if args.date_to:
        result['date_to'] = args.date_to
    if args.direct:
        result['direct'] = args.direct
    if args.return_from:
        result['return_from'] = args.return_from
    if args.return_to:
        result['return_to'] = args.return_to
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
    limit = optional_params['limit'] if 'limit' in optional_params else 10
    URL = 'https://api.skypicker.com/flights'
    PARAMS = {'flyFrom': from_city, 'to': to_city, 'dateFrom': date_from, 'date_to': date_to, 'partner': 'picky', 'limit': limit}
    if 'max_price' in optional_params:
        PARAMS['max_price'] = optional_params['max_price']
    if 'return_from' in optional_params:
        PARAMS['return_from'] = optional_params['return_from'].strftime('%d/%m/%Y')
    if 'return_to' in optional_params:
        PARAMS['return_to'] = optional_params['return_to'].strftime('%d/%m/%Y')
    if 'direct' in optional_params:
        PARAMS['direct_flights'] = 1 if optional_params['direct'] else 0
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


def print_format_table():
    for style in range(8):
        for fg in range(30, 38):
            s1 = ''
            for bg in range(40, 48):
                format = ';'.join([str(style), str(fg), str(bg)])
                s1 += '\x1b[%sm %s \x1b[0m' % (format, format)
            print(s1)
        print('\n')


def str_to_bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
