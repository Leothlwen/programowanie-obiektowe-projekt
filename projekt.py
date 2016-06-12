import pygame, math, sys, os ,termios, fcntl, platform
import random, time
import socket
import json
import select

def console_clear():
    sys.stdout.write("\x1b[2J\x1b[H")

class Game:
    state=0
    key=0
    changes=False

    def menu(self,option):
        if option==0:
            print("1.New game.")
            c=self.controls()
            while not c:
                c=self.controls()
                if c=='1':
                    console_clear()
                    self.new_game()
            
    def new_game(self,player=None):
        if player!=None:
            self.state=State(player)
            self.game_loop()
        else:
            self.state=State()
            self.game_loop()
            
    def game_loop(self):
        while True:
            if self.changes:
                self.changes=False
                self.state.display()
            self.key=self.controls()
            if self.update_state():
                break
                
    def controls(self):
        fd = sys.stdin.fileno()

        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)
        
        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

        try:
            c = sys.stdin.read(1)
            if c:
                self.changes=True
                return c
        except IOError: pass
        
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
            fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
    
    def update_state(self):
        if self.key:
            k=self.key
            msg=""
            if 'w' in k:
                msg=self.state.change_pos((-1,0))
            if 'a' in k:
                msg=self.state.change_pos((0,-1))
            if 's' in k:
                msg=self.state.change_pos((1,0))
            if 'd' in k:
                msg=self.state.change_pos((0,1))
            if 'f' in k:
                self.state.attack()
            self.state.run_ai()
            if self.state.remove_dead():
                print("Game over!")
                return True
            if msg=="next_level":
                self.new_game(self.state.player)    
    
    
justif=11
def ptos(pref,pair):
    (x,y)=pair
    return (pref+' '+str(x)+'/'+str(y)).ljust(justif)
    
def ptosr(pref,pair):
    (x,y)=pair
    return (pref+' '+str(x)+'/'+str(y)).rjust(justif)
    
    
class State:
    player=0
    monsters=0
    floor=0

    def __init__(self,player=None):
        self.floor=Floor()
        startpos=self.floor.generate(64,64)
        if player==None:
            self.player=Player()
            self.player.generate(startpos)
        else:
            self.player=player
            self.player.set_pos(startpos)
        self.monsters=self.floor.place_monsters(self.player.level)

    def display(self):
        table=self.floor.display(self.player.get_pos())
        rows=self.floor.rows//2
        columns=self.floor.columns//2
        table[rows]=table[rows][:columns]+'@'+table[rows][columns+1:]
        for m in self.monsters:
            chk=m.pos_to_table(self.player.get_pos(),columns,rows)
            if chk:
                (a,b)=chk
                table[a]=table[a][:b]+m.sign+table[a][b+1:]
        self.draw_ui(table)
        to_flush=""
        for i in range(len(table)):
            if(i==len(table)-1):
                to_flush+=table[i]
            else:
                to_flush+=table[i]+"\n"
        console_clear()
        print (to_flush,"")

    def draw_ui(self,table):
        rows=self.floor.rows
        columns=self.floor.columns
        mclose=self.closest_monsters()
        temp=mclose[0]
        temp=self.player.name+' '*(columns-(len(self.player.name)+len(temp)))+temp
        table[0]=temp
        table[-1]=self.last_log()
        table[1]=ptos('hp ',self.player.hp)+table[1][justif:]
        table[2]=ptos('mp ',self.player.mana)+table[2][justif:]
        table[3]=('lvl '+str(self.player.level)).ljust(justif)+table[3][justif:]
        table[4]=ptos('exp',self.player.experience)+table[4][justif:]
        table[5]=('att '+str(self.player.attack)).ljust(justif)+table[5][justif:]
        table[6]=('def '+str(self.player.defense)).ljust(justif)+table[6][justif:]
        print(mclose)
        if(mclose[1]):
            for i in range(len(mclose[1])):
                j=mclose[1][i]
                table[i*4+1]=table[i*4+1][:-justif]+ptosr('hp ',self.monsters[j].hp)
                table[i*4+2]=table[i*4+2][:-justif]+ptosr('mp ',self.monsters[j].mana)
                table[i*4+3]=table[i*4+3][:-justif]+('att '+str(self.monsters[j].attack)).rjust(justif)
                table[i*4+4]=table[i*4+4][:-justif]+('def '+str(self.monsters[j].defense)).rjust(justif)
    
    def remove_dead(self):
        for m in self.monsters:
            (a,b)=m.hp
            if a<=0:
                self.player.add_exp(m.bounty)
                self.monsters.remove(m)
        (a,b)=self.player.hp
        if a<=0:
            return True
    
    def monsters_to_tab(self):
        ret=[]
        for m in self.monsters:
            ret.append(m.get_pos())
        return ret
    
    def run_ai(self):
        for i in self.monsters:
            mtab=self.monsters_to_tab()
            i.run_ai(self.floor.environment,self.player,mtab)
    
    def closest_monsters(self):
        ret=["",[]]
        for m in self.monsters:
            tab=neighbours(m.get_pos())
            tab.append(m.get_pos())
            if self.player.get_pos() in tab:
                ret[0]=ret[0]+m.name+" "
                ret[1].append(self.monsters.index(m))
        if ret[0]:
            ret[0]=ret[0][:-1]
        return ret
        
    def last_log(self):
        return ""
    
    def change_pos(self,pair):
        (x,y)=addpair(self.player.get_pos(),pair)
        if self.floor.environment[x][y]==' ':
            (a,b)=self.player.get_pos()
            self.player.change_pos(pair)
        if self.floor.environment[x][y]=='/':
            return "next_level"
    
    def attack(self):
        for pairs in neighbours(self.player.get_pos()):
            for m in self.monsters:
                if m.get_pos()==pairs:
                    m.change_hp((-self.player.attack,0))
        for m in self.monsters:
            if m.get_pos()==self.player.get_pos():
                m.change_hp((-self.player.attack,0))

def addpair(g,h):
    (a,b)=g
    (c,d)=h
    return (a+c,b+d)
    
class Player:
    hp=0
    mana=0
    level=0
    experience=0
    attack=0
    defense=0
    position=0
    name=""

    def generate(self,pos,name="No Name"):
        self.hp=(20,20)
        self.mana=(10,10)
        self.level=1
        self.experience=(0,50)
        self.attack=10
        self.defense=5
        self.position=pos
        self.name=name
        self.lvlstats=[5,5,20,2,1]

    def set_pos(self,pair):
        self.position=pair

    def get_pos(self):
        return self.position

    def change_hp(self,amount):
        (a,b)=amount
        if a<-self.defense:
            self.hp=addpair(self.hp,(a+self.defense,b))

    def change_mana(self,amount):
        self.mana=addpair(self.mana,amount)

    def change_pos(self,pair):
        self.position=addpair(self.position,pair)

    def add_exp(self,amount):
        (a,b)=self.experience
        self.experience=(a+amount,b)
        if a+amount>=b:
            self.level_up()

    def level_up(self):
        self.hp=(self.hp[1]+self.lvlstats[0],self.hp[1]+self.lvlstats[0])
        self.mana=(self.mana[1]+self.lvlstats[1],self.mana[1]+self.lvlstats[1])
        self.level+=1
        self.experience=(0,self.experience[1]+self.lvlstats[2])
        self.attack+=self.lvlstats[3]
        self.defense+=self.lvlstats[4]

class Unit:
    hp=0
    mana=0
    attack=0
    defense=0
    position=0
    bounty=0
    sign=''
    name=""

    def __init__(self,pair,table=[20,10,5,0,10,'M',"Monster"]):
        self.hp=(table[0],table[0])
        self.mana=(table[1],table[1])
        self.attack=table[2]
        self.defense=table[3]
        self.bounty=table[4]
        self.sign=table[5]
        self.position=pair
        self.name=table[6]

    def pos_to_table(self,pair,columns,rows):
        (a,b)=self.position
        (c,d)=pair
        if a+rows in range(c,c+2*rows):
            if b+columns in range(d,d+2*columns):
               return (a+rows-c,b+columns-d)

    def get_pos(self):
        return self.position

    def change_hp(self,amount):
        self.hp=addpair(self.hp,amount)

    def change_mana(self,amount):
        self.mana=addpair(self.mana,amount)

    def change_pos(self,pair):
        self.position=addpair(self.position,pair)

    def set_pos(self,pair):
        self.position=pair

    def run_ai(self,environment,player,monsters):
        dist=distance(self.position,player.position)
        if dist<=1.01:
            player.change_hp((-self.attack,0))
        elif dist<5:
            self.move_to(environment,player.position,monsters)

    def move_to(self,environment,pair,monsters):
        x=neighbours(self.position)
        dist=[]
        for i in x:        
            dist.append(distance(i,pair))
        dist=order_list(dist)
        for i in dist:
            (a,b)=x[i]
            if environment[a][b]==' ' and (a,b)!=pair and (a,b) not in monsters:
                (c,d)=self.position
                self.set_pos(x[i])
                return
                
        
def order_list(values):
    ret=[]
    for i in range(len(values)):
        ind=values.index(min(values))
        ret.append(ind)
        values[ind]=999999
    return ret
        
def neighbours(pair):
    ret=[]
    ret.append(addpair(pair,(0,1)))
    ret.append(addpair(pair,(0,-1)))
    ret.append(addpair(pair,(1,0)))
    ret.append(addpair(pair,(-1,0)))
    return ret

def distance(h,g):
    (a,b)=h
    (c,d)=g
    return ((a-c)**2+(b-d)**2)**0.5

class Floor:
    environment=0
    rows=0
    columns=0
    row_offset=0
    column_offset=0

    def display(self,pair):
        (x,y)=pair
        ret=[]
        for i in range(x-int(self.rows//2),x+int(self.rows//2)):
            done=True
            if i<0 or i>63:
                ret.append('#'*self.columns)
                done=False
            if done:
                app=[]
                for j in range(y-int(self.columns//2),y+int(self.columns//2)):
                    if j<0 or j>63:
                        app.append("#")#,end="")
                    else:
                        app.append(self.environment[i][j])#,end="")
                ret.append(''.join(app))
        return ret

    def change_tile(self,tile_pos,tile):
        (x,y)=tile_pos
        self.environment[x][y]=tile

    def place_monsters(self,level):
        monsters=[]
        mtab=[]
        for i in range(0,20):
            x=random.randint(0,63)
            y=random.randint(0,63)
            while self.environment[x][y]!=' ' or (x,y) in mtab:
                x=random.randint(0,63)
                y=random.randint(0,63)
            mtab.append((x,y))
            tmon=Unit((x,y),[20+3*level,10+2*level,5+level,0+level,10+level*5,'M',"Monster"])
            monsters.append(tmon)
        return monsters

    def generate(self,x,y):
        table = []
        pointlist = self.generatepoints(x,y)
        self.pointlist=pointlist
        for i in range(y):
            eks = []
            for j in range(x):
                for (xp,yp,off) in pointlist:
                    if i in range(yp-off+1,yp+off):
                        if j in range(xp-off+1,xp+off):
                            eks.append(' ')
                    if i==yp-off or i==yp+off:
                        if j==xp-off or j==xp+off:
                            eks.append('#')
                if len(eks)!=j+1:
                    eks.append('#')
            table.append(eks)
        carvetable=self.carve(pointlist)
        for i in range(len(pointlist)):
            nonewcorridor=True
            while nonewcorridor:
                for j in carvetable[i][1:]:
                    k=random.randint(0,1)
                    if k:
                        (xp,yp,off)=pointlist[i]
                        (xp2,yp2,off2)=pointlist[j]
                        if xp2>xp:
                            for k in range(xp,xp2):
                                table[k][yp]=' '
                        elif xp>xp2:
                            for k in range(xp2,xp):
                                table[k][yp]=' '
                        elif yp>yp2:
                            for k in range(yp2,yp):
                                table[xp][k]=' '
                        elif yp2>yp:
                            for k in range(yp,yp2):
                                table[xp][k]=' '
                        nonewcorridor=False
        startpos=pointlist[random.randint(0,63)]
        endpos=pointlist[random.randint(0,63)]
        while endpos==startpos:
            endpos=pointlist[random.randint(0,63)]
        (ex,ey,eoff)=endpos
        table[ex][ey]="/"
        self.environment=table
        current_os=platform.system()
        if current_os=='Windows':
            sz=os.get_terminal_size()
            self.rows=sz.lines
            self.columns=sz.columns
        else:
            self.rows, self.columns = os.popen('stty size', 'r').read().split()
            self.rows=int(self.rows)#-self.row_offset*2
            self.columns=int(self.columns)#-self.column_offset*2"""
        self.row_offset=1
        self.column_offset=10
        (sx,sy,soff)=startpos
        return (sx,sy)

    def carve(self,pointlist):
        ret=[]
        st=8
        for i in range(len(pointlist)):
            temp=[i]
            (xp,yp,off) = pointlist[i]
            for j in range(len(pointlist)):
                (xp2,yp2,off2)=pointlist[j]
                if((xp2==xp+st and yp2==yp) or (xp2==xp and yp2==yp+st) or
                    (xp2==xp-st and yp2==yp) or (xp2==xp and yp2==yp-st)):
                    temp.append(j)
            ret.append(temp)
        return ret

    def generatepoints(self,x,y):
        plist = []
        stala=4
        for i in range(64):
            plist.append((int(x/8*(i%8)+stala),int(y/8*(i//8)+stala),int(x/16-1)))
        return plist
        
game=Game()
game.menu(0)
