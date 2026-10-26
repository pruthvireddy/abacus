"""Signal primitives tested independently of the primary comparison freeze."""
from dataclasses import dataclass


def breakout(previous_close,close,level,side,buffer=.25):
    """Both prices compared with the SAME known boundary; no moving-level cross."""
    return side*(previous_close-level)<=0 and side*(close-level)>=buffer


def touch(previous_close,high,low,level,approach_side,tolerance=.25):
    return approach_side*(previous_close-level)>0 and low<=level+tolerance and high>=level-tolerance


@dataclass(frozen=True)
class Arm:
    side:int
    origin:int
    session:str
    level:float
    poc:float

    def availability(self,minute,session,opposite_breakout=False,expiry=60):
        if session!=self.session or minute>=360:return 'session_cancelled'
        if opposite_breakout:return 'opposite_cancelled'
        if minute-self.origin>expiry:return 'expired'
        if minute==self.origin:return 'same_bar_not_allowed'
        return 'armed'


def retest(previous_close,high,low,close,level,side,tolerance=.25):
    if not touch(previous_close,high,low,level,side,tolerance):return 'no_touch'
    if side*(close-level)<-tolerance:return 'failed_retest_cancelled'
    if side*(close-level)<0:return 'unconfirmed'
    return 'confirmed'


def selected_hvn_touches(previous_close,high,low,saved_nodes,tolerance=.25):
    """Saved pre-bar identity/band survives a price-containing post-bar removal."""
    result=[]
    for node in saved_nodes:
        side=node['side']  # overhead +1 -> short; lower -1 -> long
        approach=previous_close<node['lo'] if side==1 else previous_close>node['hi']
        if approach and low<=node['hi']+tolerance and high>=node['lo']-tolerance:
            result.append(dict(node,direction=-side))
    return result


def confirmed_hvn(node,close):
    return close<node['lo'] if node['side']==1 else close>node['hi']


class Lockout:
    def __init__(self,minutes=15):self.minutes=minutes;self.accepted={}
    def accept(self,setup,side,minute,session):
        key=(session,setup,side)
        prior=self.accepted.get(key)
        if prior is not None and minute-prior<self.minutes:return False
        self.accepted[key]=minute
        return True


def entry_status(signal_time,next_time,next_minute,minute_ns=60_000_000_000):
    if next_time is None or next_time!=signal_time+minute_ns:return 'missing_next_minute'
    if not 120<=next_minute<360:return 'outside_entry_window'
    return 'next_open_eligible'
