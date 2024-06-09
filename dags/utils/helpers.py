from datetime import date, timedelta, datetime
import pytz
import sys


if __name__ == '__main__':
    from constants import SG_TIMEZONE
else:
    from .constants import SG_TIMEZONE


sgTz = pytz.timezone(SG_TIMEZONE) 

def getCurrentDate() -> str:
    todayStr = datetime.now(sgTz).strftime('%Y%m%d')
    # print(todayStr)
    return todayStr


def getNextDayDate() -> str:
    tmr = datetime.now(sgTz) + timedelta(1)
    tmrStr = tmr.strftime('%Y%m%d')
    # print(tmrStr)
    return tmrStr


def getCurrentTimeStamp()->str:
    ts = datetime.now(sgTz)
    tsStr = ts.strftime('%Y%m%d%H%M%S')
    # print(tsStr)
    return tsStr


if __name__ == "__main__":
    
    print(SG_TIMEZONE)
    getCurrentDate()
    getNextDayDate()
    getCurrentTimeStamp()
