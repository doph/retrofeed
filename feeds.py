# Standard library imports
import datetime as dt
import random
import textwrap as tw
import time
import yaml
from types import SimpleNamespace

# Retrofeed imports
from modules import ap_news, finance, weather, spot_the_station
from modules import string_processing as sp

class BaseFeed(object):
    '''Base class for all feeds, handles config and slow printing'''
    def __init__(self):
        self.update_message = None
        self.data = {}
        self.content = None
        self._set_config()
        self.config.header = None
        self.config.update_message = None
    
    def _set_config(self):
        '''Load the config from the config file'''
        with open('config.yaml', 'r') as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
        self.config = SimpleNamespace(**cfg['base'])

    def get_config(self) -> dict:
        '''Return the config as a dict'''
        if not isinstance(self.config, SimpleNamespace):
            raise TypeError("Config not initialized properly")
        return vars(self.config)
    
    def _update_config(self, dict: dict):
        '''Update the config with the passed dict'''
        cfg = self.get_config()
        cfg.update(dict)
        self.config = SimpleNamespace(**cfg)

    def _slowp(self, s='', end='\n',):
        '''Slow Print
        Similar to print() but with fun options
        Wraps words at wrap_width characters if it is non-zero'''
        if len(s) > self.config.line_width:
            lines = tw.wrap(s, self.config.line_width)
            # Call self for each line, but with wrapping off...
            for line in lines:
                self._slowp(line, end=end)
            return
        for c in s:
            print(c, end='', flush=True)
            time.sleep(self.config.print_delay) 
        print(end, end='', flush=True)
        time.sleep(self.config.print_delay)

    def _slown(self):
        '''Slow Newline
        Prints n spaces with a delay, then returns
        Picks a random position to pause to stave off
        screen burn-in (default = 0 = no pause)'''
        pause_pos = random.randrange(self.config.line_width)
        for i in range(self.config.line_width):
            print(' ', end='', flush=True)
            time.sleep(self.config.newline_delay)
            if i == pause_pos:
                time.sleep(self.config.pause_time)
        print(flush=True)
        time.sleep(self.config.print_delay)

    def _print_update_msg(self):
        '''Display passed string as an "updating..." message'''
        self._slowp(f'[{self.config.update_message}', end='')
        for i in range(3):
            time.sleep(self.config.subsegment_delay)
            self._slowp('.', end='')
        time.sleep(self.config.subsegment_delay)
        self._slowp(']')
        self._slown()

    def _get_header(self, header) -> str:
        '''Display the passed string as a segment header, surrounded by markers'''
        left_marker, string, right_marker = header
        string = string.strip().upper()

        num_markers = 0
        if len(string) + 4 < self.config.line_width:
            num_markers = int((self.config.line_width - 4 - len(string)) / 2)

        header_string = f"{left_marker * num_markers} {string} {right_marker * num_markers}"
        return header_string

    def _refresh_data(self):
        #TODO: implement optional data cache across feed instances
        data_age = dt.datetime.now() - self.data.get('fetched_on', dt.datetime.min)
        if data_age >= dt.timedelta(minutes=self.config.refresh):
            if self.config.verbose_updates and self.config.update_message is not None:
                self._print_update_msg()
            self._set_data()

    def show(self):
        self._slown()
        self._slown()
        self._refresh_data()
        self._set_content()
        if self.config.header is not None:
            header = self._get_header(self.config.header)
            self._slowp(header)
        self._slown()
        for line in self.content:
            if line == '':
                self._slown()
            else:
                self._slowp(line)
        self._slown()
        time.sleep(self.config.segment_delay)

    def _set_data(self):
        '''Set the data for the feed
        This method should be overridden by child classes'''
        raise NotImplementedError
    
    def _set_content(self):
        '''Set the content of the feed
        This method should be overridden by child classes'''
        raise NotImplementedError


class Title(BaseFeed):
    def __init__(self):
        super().__init__()

    def show(self):
        '''Override show() since the title card is a special case'''
        headspace = "\n" * int(self.config.line_width / 2)
        print(headspace)
        self._slowp(f"{self.config.title} - VERSION {self.config.version}")
        self._slowp(f"{self.config.credit}")


class DatetimeFeed(BaseFeed):
    def __init__(self, config: dict):
        super().__init__()
        self._update_config(config)

    def _refresh_data(self):
        ''' Since this Feed is so simple, override this method to do nothing
        and do all the work in set_content()'''
        pass

    def _set_content(self):
        self.content = []
        now = dt.datetime.now()
        date_text = now.strftime(self.config.format)
        day_num = now.day
        date_text += str(day_num)
        if day_num in (1, 21, 31):
            date_text += 'st'
        elif day_num in (2, 22):
            date_text += 'nd'
        elif day_num in (3, 23):
            date_text += 'rd'
        else:
            date_text += 'th'
        time_text = sp.format_time(now)
        if self.config.descriptive:
            self.content.append(f"It is {date_text}")
            self.content.append(f"Current time is {time_text}")
        else:
            self.content.append(f"{time_text} {date_text}")


class FinanceFeed(BaseFeed):
    def __init__(self, config: dict):
        super().__init__()
        self._update_config(config)

    def _set_data(self):
        self.data = finance.get_finance(self.config.symbols)

    def _set_content(self):
        self.content = []       
         
        if 'CLOSED' in self.data['market_message'].upper():
            self.content.append(self.data['market_message'])
        else:
            self.content.append(f"As of {sp.format_time(self.data['fetched_on'])}")
        
        for i in self.data['indexes']:
            self.content.append('')
            self.content.append(f"    {i['name']:9}  {i['price']:>9}")
            self.content.append(f"               {i['delta']:>9}  {i['delta_pct']}")


class NewsFeed(BaseFeed):
    def __init__(self, config: dict):
        super().__init__()
        self._update_config(config)
        self.current_index = 0

    def _set_data(self):
        self.data = ap_news.get_news()
        #TODO: implement max news items

    def _set_content(self):
        self.content = []

        if not self.config.cycle:
            self.current_index = 0
        items = min(self.config.items, len(self.data['items']))
        for i in range(1, items+1):
            self.current_index += i
            if self.current_index >= len(self.data['items']):
                self.current_index = 0
            self.content.append('')
            self.content.append(self.data['items'][self.current_index]['headline'])
            if self.config.show_summary:
                self.content.append('')
                self.content.append(self.data['items'][self.current_index]['summary'])
                self.content.append('')


class WeatherFeed(BaseFeed):
    def __init__(self, config: dict):
        super().__init__()
        self._update_config(config)

    def _set_data(self):
        self.data = weather.get_weather(self.config.lat, self.config.lon, self.config.location)

    def _set_content(self):
        self.content = []

        self.content.append(f"Weather at {self.data['location']}")
        self.content.append(f"As of {self.data['last_update']}")
        
        if len(self.data['hazards']) > 0:
            for hazard in self.data['hazards']:
                self.content.append('')
                self.content.append(f"!!! {hazard}")
                
        self.content.append('')
        self.content.append(f"    Conditions   {self.data['currently']}")
        self.content.append(f"    Temperature  {self.data['temp_f']} ({self.data['temp_c']})")
        self.content.append(f"    Wind         {self.data['wind_speed']}")
        self.content.append(f"    Visibility   {self.data['visibility']}")
        self.content.append(f"    Dewpoint     {self.data['dewpoint']} {self.data['comfort']}")

        forecast_periods = min(self.config.periods, len(self.data['periods']))
        if forecast_periods > 0:
            self.content.append('')
            if forecast_periods > 1:
                header = self._get_header(['*', 'Extended Forecast...', '*'])
                self.content.append(header)
            for period in self.data['periods'][:forecast_periods]:
                self.content.append('')
                self.content.append(period['timeframe'])
                self.content.append(period['forecast'])


class ISSFeed(BaseFeed):
    def __init__(self, config: dict):
        super().__init__()
        self._update_config(config)

    def _set_data(self):
        self.data = spot_the_station.get_sightings(self.config.country,
                                                   self.config.region,
                                                   self.config.city,
                                                   )

    def _set_content(self):
        self.content = []

        # Exit early if nothing to show
        sightings = self.data['sightings']
        if len(sightings) == 0:
            self.content.append('No ISS Sightings Available')
        else:
            self.content.append(self.data['location'])
            self.content.append('Upcoming ISS Sightings:')
            num_shown = 0
            cutoff_dt = dt.datetime.now()
            for s in sightings:
                if s['date_time'] >= cutoff_dt and num_shown < self.config.max_sightings:
                    self.content.append('')
                    self.content.append(f"    {s['date_text']} @ {s['time_text']}")
                    self.content.append(f"      Visible for {s['visible']}")
                    self.content.append(f"      Max height {s['max_height']} Degrees")
                    self.content.append(f"      From {s['appears']}")
                    self.content.append(f"      To   {s['disappears']}")
                    num_shown += 1
