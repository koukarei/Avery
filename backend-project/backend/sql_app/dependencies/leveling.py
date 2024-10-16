
def level_up(xp:int,level:int):
    total_xp_to_level_up=2**(level-1)+80
    if xp>=total_xp_to_level_up:
        level+=1
        xp=0
    return xp,level