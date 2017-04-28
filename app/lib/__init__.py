from datetime import date
from dateutil.relativedelta import MO, TH
from dateutil.relativedelta import relativedelta as rd
from holidays import HolidayBase


class NYCHolidays(HolidayBase):
    def __init__(self, **kwargs):
        self.country = 'US'
        HolidayBase.__init__(self, **kwargs)

    def _populate(self, year):
        # New Year's Day
        if year > 1870:
            name = "New Year's Day"
            self[date(year, 1, 1)] = name
            if self.observed and date(year, 1, 1).weekday() == 6:
                self[date(year, 1, 1) + rd(days=+1)] = name + " (Observed)"
            elif self.observed and date(year, 1, 1).weekday() == 5:
                # Add Dec 31st from the previous year without triggering
                # the entire year to be added
                expand = self.expand
                self.expand = False
                self[date(year, 1, 1) + rd(days=-1)] = name + " (Observed)"
                self.expand = expand
            # The next year's observed New Year's Day can be in this year
            # when it falls on a Friday (Jan 1st is a Saturday)
            if self.observed and date(year, 12, 31).weekday() == 4:
                self[date(year, 12, 31)] = name + " (Observed)"

        # Martin Luther King, Jr. Day
        if year >= 1986:
            name = "Martin Luther King, Jr. Day"
            self[date(year, 1, 1) + rd(weekday=MO(+3))] = name

        # Washington's Birthday
        name = "Washington's Birthday"
        if year > 1970:
            self[date(year, 2, 1) + rd(weekday=MO(+3))] = name
        elif year >= 1879:
            self[date(year, 2, 22)] = name

        # Memorial Day
        if year > 1970:
            self[date(year, 5, 31) + rd(weekday=MO(-1))] = "Memorial Day"
        elif year >= 1888:
            self[date(year, 5, 30)] = "Memorial Day"

        # Independence Day
        if year > 1870:
            name = "Independence Day"
            self[date(year, 7, 4)] = name
            if self.observed and date(year, 7, 4).weekday() == 5:
                self[date(year, 7, 4) + rd(days=-1)] = name + " (Observed)"
            elif self.observed and date(year, 7, 4).weekday() == 6:
                self[date(year, 7, 4) + rd(days=+1)] = name + " (Observed)"

        # Labor Day
        if year >= 1894:
            self[date(year, 9, 1) + rd(weekday=MO)] = "Labor Day"

        # Columbus Day
        name = "Columbus Day"
        if year >= 1970:
            self[date(year, 10, 1) + rd(weekday=MO(+2))] = name
        elif year >= 1937:
            self[date(year, 10, 12)] = name

        # Election Day
        if year >= 2015:
            dt = date(year, 11, 1) + rd(weekday=MO)
            self[dt + rd(days=+1)] = "Election Day"

        # Veterans Day
        if year > 1953:
            name = "Veterans Day"
        else:
            name = "Armistice Day"
        if 1978 > year > 1970:
            self[date(year, 10, 1) + rd(weekday=MO(+4))] = name
        elif year >= 1938:
            self[date(year, 11, 11)] = name
            if self.observed and date(year, 11, 11).weekday() == 5:
                self[date(year, 11, 11) + rd(days=-1)] = name + " (Observed)"
            elif self.observed and date(year, 11, 11).weekday() == 6:
                self[date(year, 11, 11) + rd(days=+1)] = name + " (Observed)"

        # Thanksgiving
        if year > 1870:
            self[date(year, 11, 1) + rd(weekday=TH(+4))] = "Thanksgiving"

        # Christmas Day
        if year > 1870:
            name = "Christmas Day"
            self[date(year, 12, 25)] = "Christmas Day"
            if self.observed and date(year, 12, 25).weekday() == 5:
                self[date(year, 12, 25) + rd(days=-1)] = name + " (Observed)"
            elif self.observed and date(year, 12, 25).weekday() == 6:
                self[date(year, 12, 25) + rd(days=+1)] = name + " (Observed)"
