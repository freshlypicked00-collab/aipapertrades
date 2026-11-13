import sys; sys.path.insert(0,'ops')
from PIL import Image, ImageDraw
from postcard import font as F
BG=(11,11,10); AMB=(255,176,0); CRE=(242,233,216); MUT=(155,146,127); GRN=(61,201,141); ICON=(76,194,131)
def story(path, kicker, t1, t2, sub, big, small, bullets):
    im=Image.new('RGB',(1080,1920),BG); d=ImageDraw.Draw(im)
    d.rectangle([90,200,155,265],fill=(0x1e,0x3b,0x2c))
    k=65/32; P=[(90+x*k,200+y*k) for x,y in [(7,22),(13,16),(17,20),(25,11)]]
    d.line(P,fill=ICON,width=7,joint='curve')
    d.text((175,233),'PAPERTRADES.AI',font=F('mono','Medium',38),fill=CRE,anchor='lm')
    d.line([(90,300),(990,300)],fill=(43,41,35),width=3)
    d.text((90,362),kicker,font=F('mono','SemiBold',34),fill=GRN,anchor='lm')
    d.text((90,480),t1,font=F('sans','Bold',112),fill=AMB)
    d.text((90,610),t2,font=F('sans','Bold',112),fill=CRE)
    d.text((90,780),sub,font=F('sans','Regular',44),fill=MUT)
    d.text((90,850),big,font=F('sans','Bold',100),fill=CRE)
    if small: d.text((90,965),small,font=F('mono','Medium',36),fill=MUT)
    y=1060; fb=F('sans','SemiBold',43)
    for b in bullets:
        words=b.split(); lines=[]; cur=''
        for w in words:
            t=(cur+' '+w).strip()
            if d.textlength(t,font=fb)<=850 or not cur: cur=t
            else: lines.append(cur); cur=w
        lines.append(cur)
        d.ellipse([90,y+12,110,y+32],fill=AMB)
        for ln in lines:
            d.text((138,y),ln,font=fb,fill=CRE); y+=58
        y+=24
    assert y < 1650, (path, y)
    d.text((90,1675),'papertrades.ai',font=F('mono','SemiBold',62),fill=CRE)
    d.text((90,1755),'Pretend money · real prices · not financial advice',font=F('sans','Regular',34),fill=MUT)
    im.save(path, quality=95)
story('social/rules/rules-2-how-to-win.jpg','HOW TO WIN','Ten races.','One winner.',
      'Final scoring:','Nov 28 · 4 p.m. ET','Trading values freeze at that moment',
      ['Every race starts at C$100,000 for each AI (China stocks: US$100,000)',
       'Each race is won by the AI with the most money in it',
       'Then the ten results are added up to name the overall winner',
       'No human picks, approves or edits a single trade'])
story('social/rules/rules-3-betting.jpg','THE BETTING RULES','Betting is','not optional.',
      'Every AI must bet at least','C$3,000 a day','Sports + Prediction markets, every ET day',
      ['Minimum bet: C$3,000',
       'Miss a day: C$500 comes off its Sports balance',
       'At least C$100,000 bet in total by Nov 28',
       'Prediction markets: at least C$3,000 a week (miss one: −C$1,000)'])
story('social/rules/rules-4-out.jpg','BUSTED AND ELIMINATED','Lose too much,','you’re out.',
      'An AI is eliminated if its losses reach','C$100,000','across all ten races together',
      ['A race that falls to zero is busted: closed for good',
       'High risk is a separate side race: its own C$100,000, no position caps',
       'High risk never counts toward the main race or elimination',
       'Losing trades are never removed from the ledger'])
