import time
_last = {}
def allow(key:str, cooldown:int)->tuple[bool,float]:
    now=time.time(); last=_last.get(key,0.0); rem=cooldown-(now-last)
    if rem>0: return False, rem
    _last[key]=now; return True, 0.0
