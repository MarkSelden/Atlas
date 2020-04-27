'''
simulation of navigation algorithms for micro-robots
'''

'''
FIXME: collect heatmap of cell occupancy during one run.
FIXME: collect CDF of cells explored, on many runs.
'''

#=== built-in
import os
import time
import random
import math
import pprint
#=== third-party
#=== local
import AtlasScenarios

#============================ defines =========================================

#=== settings

NUM_ROBOTS         = 10
UI                 = True
NUMRUNS            = 1
SCENARIOS          = [
    #'SCENARIO_OFFICE_FLOOR',
    #'SCENARIO_RAMA_CANONICAL',
    #'SCENARIO_EMPTY_SPACE',
    'SCENARIO_MINI_OFFICE_FLOOR',
    'SCENARIO_MINI_RAMA_CANONICAL',
    'SCENARIO_MINI_EMPTY_SPACE',
]

#=== defines

VERSION            = (1,0)

HEADING_N          = 'N'
HEADING_NE         = 'NE'
HEADING_E          = 'E'
HEADING_SE         = 'SE'
HEADING_S          = 'S'
HEADING_SW         = 'SW'
HEADING_W          = 'W'
HEADING_NW         = 'NW'
HEADING_ALL        = [
    HEADING_N, 
    HEADING_NE,
    HEADING_E,
    HEADING_SE,
    HEADING_S,
    HEADING_SW,
    HEADING_W,
    HEADING_NW,
]

#============================ variables =======================================

pp =  pprint.PrettyPrinter()

#============================ helper functions ================================

def genRealMapDrawing(drawing):
    realMap   = []
    startPos  = None
    row       = 0
    col       = 0
    for line in drawing.splitlines():
        if not line.startswith('#'):
            continue
        realMap += [[]]
        for c in line:
            if   c=='#':
                realMap[-1] += [0]
            elif c==' ':
                realMap[-1] += [1]
            elif c=='S':
                realMap[-1] += [1]
                assert startPos==None
                startPos = (row,col)
            else:
                raise SystemError()
            col   += 1
        row  += 1
        col   = 0
    return (realMap,startPos)

def printDiscoMap(discoMap,startPos,robotPositions,kpis,rankMapStart=None):
    output         = []
    numUnExplored  = 0
    output        += ['']
    numRows        = len(discoMap)
    numCols        = len(discoMap[0])
    numCells       = numRows*numCols
    for row in range(len(discoMap)):
        line = []
        for col in range(len(discoMap[row])):
            while True:
                # robot
                robotFound = False
                for (ri,(rx,ry)) in enumerate(robotPositions):
                    if (row,col) == (rx,ry):
                        robotFound = True
                        if rankMapStart:
                            line += ['*']
                        else:
                            line += [str(ri%10)]
                        break
                if robotFound:
                    break
                # start position
                if (row,col)==startPos:
                    line += ['S']
                    break
                # wall
                if  discoMap[row][col]==0:
                    line += ['#']
                    break
                # unexplored
                if discoMap[row][col]==-1:
                    numUnExplored += 1
                    if rankMapStart:
                        line += [' ']
                    else:
                        line += ['.']
                    break
                # rank
                if rankMapStart:
                    line += [str(rankMapStart[(row,col)]%10)]
                    '''
                    if   rankMapStart[(row,col)]%3==0:
                        line += ['$']
                    elif rankMapStart[(row,col)]%3==1:
                        line += ['>']
                    else:
                        line += ['.']
                    '''
                    break
                # explored
                line += [' ']
                break
        output += [' '.join(line)]
    output += ['']
    output += [
        'numExplored  : {0}/{1} ({2:.0f}%)'.format(
            numCells-numUnExplored,numCells,100.0*((numCells-numUnExplored)/numCells)
        )
    ]
    for k in sorted(kpis.keys()):
        output += ['{0:<13}: {1}'.format(k,kpis[k])]
    output = '\n'.join(output)
    os.system('cls')
    print(output)

#============================ classes =========================================

#======== exceptions

class MappingDoneSuccess(Exception):
    pass

class MappingDoneIncomplete(Exception):
    pass

#======== navigation algorithms

class Navigation(object):
    def __init__(self,realMap,startPos,numRobots):
        
        # store params
        self.realMap                   = realMap
        self.startPos                  = startPos
        self.numRobots                 = numRobots
        
        # local variablels
        self.numRows                   = len(self.realMap)    # shorthand
        self.numCols                   = len(self.realMap[0]) # shorthand
        self.firstIteration            = True
        self.rankMaps                  = {}
        self.discoMap                  = []
        self.allCellsIdx               = []
        self.stats                     = {}
        for (x,row) in enumerate(realMap):
            self.discoMap             += [[]]
            for (y,col) in enumerate(row):
                self.discoMap[-1]     += [-1]
                self.allCellsIdx      += [(x,y)]
    
    def getStats(self):
        return self.stats
    
    def _determineDoneExploring(self):
        fullDiscoMap = True
        for row in self.discoMap:
            for cell in row:
                if cell == -1:
                    fullDiscoMap = False
                    break
        if fullDiscoMap:
            raise MappingDoneSuccess
    
    def _OneHopNeighborhood(self,x,y):
        returnVal = []
        for (nx,ny) in [
                (x-1,y-1),(x-1,y  ),(x-1,y+1),
                (x  ,y-1),          (x  ,y+1),
                (x+1,y-1),(x+1,y  ),(x+1,y+1),
            ]:
            
            # only consider cells inside the realMap
            if  (
                    (nx>=0)            and
                    (nx<self.numRows)  and
                    (ny>=0)            and
                    (ny<self.numCols)
                ):
                returnVal += [(nx,ny)]
            
        return returnVal
    
    def _TwoHopNeighborhood(self,x,y):
        returnVal = []
        for (nx,ny) in [
                (x-2,y-2),(x-2,y-1),(x-2,y  ),(x-2,y+1),(x-2,y+2),
                (x-1,y-2),                              (x-1,y+2),
                (x  ,y  ),                              (x  ,y+2),
                (x+1,y-2),                              (x+1,y+2),
                (x+2,y-2),(x+2,y-1),(x+2,y  ),(x+2,y+1),(x+2,y+2)
            ]:
            
            # only consider cells inside the realMap
            if  (
                    (nx>=0)            and
                    (nx<self.numRows)  and
                    (ny>=0)            and
                    (ny<self.numCols)
                ):
                returnVal += [(nx,ny)]
                
        return returnVal

#=== distributed

class NavigationDistributed(Navigation):

    def think(self, robotPositions):
        
        # returnVal
        nextRobotPositions   = []
        
        # determine whether we're done exploring
        self._determineDoneExploring()
        
        # move each robot
        for (ridx,(rx,ry)) in enumerate(robotPositions):
            
            # explore your neighborhood
            validNextPositions = []
            
            for (nx,ny) in self._OneHopNeighborhood(rx,ry):
                
                # populate the discovered map
                if   self.realMap[nx][ny] == 0:
                    self.discoMap[nx][ny]=0
                elif self.realMap[nx][ny] == 1:
                    self.discoMap[nx][ny]=1
                
                # a valid next position is one with no wall or robot
                if  (
                        (self.realMap[nx][ny]==1) and
                        ((nx,ny) not in nextRobotPositions)
                    ):
                    validNextPositions += [(nx,ny)]
            
            # move robot to randomly chosen valid neighbor
            if validNextPositions:
                nextRobotPositions += [self._pickNextPosition(ridx,rx,ry,validNextPositions)]
            else:
                nextRobotPositions += [(rx,ry)]
        
        return (nextRobotPositions,self.discoMap,None)
    
    def _pickNextPosition(self,ridx,rx,ry,validNextPositions):
        raise SystemError()
    
class NavigationRandomWalk(NavigationDistributed):
    
    def _pickNextPosition(self,ridx,rx,ry,validNextPositions):
        return random.choice(validNextPositions)

class NavigationBallistic(NavigationDistributed):

    def __init__(self,realMap,startPos,numRobots):
        NavigationDistributed.__init__(self,realMap,startPos,numRobots)
        self.robotHeading = []
        for _ in range(self.numRobots):
            self.robotHeading += [random.choice(HEADING_ALL)]

    def _pickNextPosition(self,ridx,rx,ry,validNextPositions):
        
        nextPosition = None
        
        while not nextPosition:
            # compute next position
            # FIXME: box
            if   self.robotHeading[ridx]==HEADING_N:
                nextPosition = (rx-1,ry  )
            elif self.robotHeading[ridx]==HEADING_NE:
                nextPosition = (rx-1,ry+1)
            elif self.robotHeading[ridx]==HEADING_E:
                nextPosition = (rx  ,ry+1)
            elif self.robotHeading[ridx]==HEADING_SE:
                nextPosition = (rx+1,ry+1)
            elif self.robotHeading[ridx]==HEADING_S:
                nextPosition = (rx+1,ry  )
            elif self.robotHeading[ridx]==HEADING_SW:
                nextPosition = (rx+1,ry-1)
            elif self.robotHeading[ridx]==HEADING_W:
                nextPosition = (rx  ,ry-1)
            elif self.robotHeading[ridx]==HEADING_NW:
                nextPosition = (rx-1,ry-1)
            else:
                raise SystemError()
            
            if nextPosition not in validNextPositions:
                self.robotHeading[ridx] = random.choice(HEADING_ALL)
                nextPosition = None
        
        return nextPosition

#=== centralized

class NavigationCentralized(Navigation):
    def __init__(self,realMap,startPos,numRobots):
        Navigation.__init__(self,realMap,startPos,numRobots)
        self.shouldvisits         = {}
        self._distance(startPos) # force rankMap to be fully built for start position
    
    def _distance(self,pos1,pos2=None):
        
        # easy answer if same position
        if pos1==pos2:
            return 0
        
        # inverting pos1 and pos2 in case pos2 already cached (same distance)
        if (pos1 not in self.rankMaps) and (pos2 in self.rankMaps):
            temp = pos1
            pos1 = pos2
            pos2 = temp
        
        # check whether rankMaps in cache, otherwise build or resume
        if  (
                (pos1 in self.rankMaps) and
                (pos2 in self.rankMaps[pos1])
            ):
                # stats
                self._stats_incr('cache_hit')
        else:
            if  (
                    (pos1 in self.rankMaps) and
                    (pos2 not in self.rankMaps[pos1])
                ):
                # resuming building the rankMap
                
                # stats
                self._stats_incr('cache_miss_resume')
                
                # local variables (resume)
                rankMap                   = self.rankMaps[pos1]
                shouldvisit               = self.shouldvisits[pos1]
            else:
                # starting new rankMap
                
                # stats
                self._stats_incr('cache_miss_new')
                
                # local variables (new)
                rankMap                   = {}
                shouldvisit               = []
                
                # start from start position
                rankMap[pos1]             = 0
                shouldvisit              += [pos1]
            
            while True:
                
                # find cell to visit with lowest rank (abort if none)
                found         = False
                currentrank   = None
                for (x,y) in shouldvisit:
                    if  (
                            currentrank==None or
                            rankMap[(x,y)]<currentrank
                        ):
                        currentrank   = rankMap[(x,y)]
                        (cx,cy)       = (x,y)
                        found = True
                if found==False:
                    break
                
                # assign a height for all its neighbors
                for (nx,ny) in self._OneHopNeighborhood(cx,cy):
                    if (nx,ny) in rankMap:
                        assert rankMap[(nx,ny)] <= currentrank+1 
                    if  (
                            (self.realMap[nx][ny]==1) and
                            ((nx,ny) not in rankMap)
                        ):
                        rankMap[(nx,ny)]     = currentrank+1
                        shouldvisit        += [(nx,ny)]
                
                # mark a visited
                shouldvisit.remove((cx,cy))
                
                # abort if I reached pos2
                if pos2 and (pos2 in rankMap):
                    self.shouldvisits[pos1] = shouldvisit
                    break
            
            self.rankMaps[pos1] = rankMap

        if pos2:
            return self.rankMaps[pos1][pos2]

    def _stats_incr(self,k):
        if k not in self.stats:
            self.stats[k] = 0
        self.stats[k] += 1

class NavigationRama(NavigationCentralized):
    
    def think(self, robotPositions):
        
        # store params
        nextRobotPositions   = robotPositions[:] # many a local copy
        
        # determine whether we're done exploring
        self._determineDoneExploring()
        
        # identify robots at the frontier
        frontierBots = []
        for (ridx,(rx,ry)) in enumerate(robotPositions):
            
            # check that robot has frontier in its 2-neighborhood
            closeToFrontier = False
            for (nx,ny) in self._TwoHopNeighborhood(rx,ry):
                if self.discoMap[nx][ny]==-1:
                    closeToFrontier = True
                    break
            if closeToFrontier==False:
                continue
            
            # check that robot has open space in its 1-neighborhood that's further than itself
            for (nx,ny) in self._OneHopNeighborhood(rx,ry):
                if (
                    self.realMap[nx][ny]==1         and  # open position (not wall)
                    ((nx,ny) not in robotPositions) and  # no robot there
                    (nx,ny)!=self.startPos          and  # not the start position
                    self._distance(self.startPos,(nx,ny))>self._distance(self.startPos,(rx,ry))
                ):
                    frontierBots += [ridx]
                    break
        
        # break if couldn't find any further robot to move
        if frontierBots==[]:
            raise MappingDoneIncomplete()
        
        # pick a frontierBot
        distanceToStart = {}
        for (ridx,(x,y)) in enumerate(robotPositions):
            if ridx not in frontierBots:
                continue
            distanceToStart[ridx] = self._distance(self.startPos,(x,y))
        frontierBot = sorted(distanceToStart.items(), key=lambda item: item[1])[0][0]
        
        # pick a cell for a new Robot
        (fx,fy) = robotPositions[frontierBot]
        while True:
            (rx,ry) = random.choice(self._OneHopNeighborhood(fx,fy))
            if  (
                    self.realMap[rx][ry]==1            and
                    ((rx,ry) not in robotPositions)    and
                    (rx,ry)!=self.startPos
                ):
                break
        
        # pick a robot to move and change its position
        distanceToStart = {}
        for (ridx,(x,y)) in enumerate(robotPositions):
            distanceToStart[ridx] = self._distance(self.startPos,(x,y))
        newBot = sorted(distanceToStart.items(), key=lambda item: item[1])[0][0]
        nextRobotPositions[newBot] = (rx,ry)
        
        # update the discoMap
        for (nx,ny) in self._OneHopNeighborhood(rx,ry):
            if   self.realMap[nx][ny]==0:
                self.discoMap[nx][ny]=0
            elif self.realMap[nx][ny]==1:
                self.discoMap[nx][ny]=1
        
        return (nextRobotPositions,self.discoMap,None)

class NavigationAtlas(NavigationCentralized):
    
    def think(self, robotPositions):
        
        # store params
        robotPositions            = robotPositions[:] # many a local copy
        
        # local variables
        robotsMoved               = []
        frontierCellsTargeted     = []
        (sx,sy)                   = self.startPos # shorthand
        
        # determine whether we're done exploring
        try:
            self._determineDoneExploring()
        except:
            self.stats['num_cache_entries'] = len(self.rankMaps)
            l = [len(v) for (k,v) in self.rankMaps.items()]
            self.stats['cache_maxlength']   = max(l)
            self.stats['cache_minlength']   = min(l)
            self.stats['cache_avglength']   = float(sum(l))/len(l)
            raise
        
        while True:
            if self.firstIteration:
                # this is my first iteration: put robot 0 in the start position
                
                mr_idx                = 0
                (mx_next,my_next)     = self.startPos
                self.firstIteration   = False
            
            else:
                # I already have robots in the area
                
                # identify all frontierCells
                frontierCells = []
                for (x,y) in self.allCellsIdx:
                    # don't consider the same call twice
                    if (x,y) in frontierCellsTargeted:
                        continue
                    # consider only open cells
                    if self.discoMap[x][y]!=1:
                        continue
                    # check wether this cell has unexplored neighbor cells
                    for (nx,ny) in self._OneHopNeighborhood(x,y):
                        if self.discoMap[nx][ny]==-1:
                            frontierCells += [((x,y),self._distance((sx,sy),(x,y)))]
                            break
                
                # keep only frontierCells with lowest rank
                frontierCells = [
                    fc[0] for fc in frontierCells
                    if fc[1]==sorted(frontierCells, key=lambda item: item[1])[0][1]
                ]
                
                # pick move robot (mv) and frontier cell (fc) to move towards
                #   Rules (most important first):
                #     - robot as close as possible to one of the target frontier cells
                #     - robot as close as possible to start position
                #     - frontier cell with many neighbors with a higher rank (avoids cutting corners)
                #     - frontier cell with many unexplored neighbors
                mr_idx                          = None
                fc_pos                          = None
                mr_distToStart                  = None
                mr_distToFc                     = None
                for (ridx,(rx,ry)) in enumerate(robotPositions):
                    
                    # don't move the same robot twice
                    if ridx in robotsMoved:
                        continue
                    
                    rDistToStart                = self._distance((sx,sy),(rx,ry))
                    max_numHigherRankNeighbors  = None
                    max_numUnexploredNeighbors  = None
                    for (fx,fy) in frontierCells:
                        rDistToFc               = self._distance((fx,fy),(rx,ry))
                        (numHigherRankNeighbors,numUnexploredNeighbors)  = self._numHigherRankAndUnexploredNeighbors(fx,fy,self.discoMap)
                        if  (
                                mr_idx==None                   or
                                rDistToFc<mr_distToFc          or
                                (
                                    rDistToFc==mr_distToFc               and
                                    rDistToStart<mr_distToStart
                                )                              or
                                (
                                    rDistToFc==mr_distToFc               and
                                    rDistToStart==mr_distToStart         and
                                    max_numHigherRankNeighbors!=None     and
                                    numHigherRankNeighbors>max_numHigherRankNeighbors
                                )                              or
                                (
                                    rDistToFc==mr_distToFc               and
                                    rDistToStart==mr_distToStart         and
                                    max_numUnexploredNeighbors!=None     and
                                    numUnexploredNeighbors>max_numUnexploredNeighbors
                                )
                            ):
                            mr_idx                     = ridx
                            fc_pos                     = (fx,fy)
                            mr_distToStart             = rDistToStart
                            mr_distToFc                = rDistToFc
                            max_numHigherRankNeighbors = numHigherRankNeighbors
                            max_numUnexploredNeighbors = numUnexploredNeighbors
                
                # abort if couldn't find robot to move
                if mr_idx==None:
                    break
                
                # pick new position
                (fx,fy)                = fc_pos                 # shorthand
                (mx_cur, my_cur)       = robotPositions[mr_idx] # shorthand
                (mx_next,my_next)      = (None,None)
                min_dist               = None
                for (x,y) in self._OneHopNeighborhood(mx_cur,my_cur):
                    if (
                        self.realMap[x][y]==1           and
                        (x,y) not in robotPositions     and
                        (
                            min_dist==None or
                            self._distance((fx,fy),(x,y))<min_dist
                        )
                    ):
                        min_dist = self._distance((fx,fy),(x,y))
                        (mx_next,my_next) = (x,y)
                
                # abort if couldn't find a position to move to
                if mx_next==None:
                    break
                
                frontierCellsTargeted += [fc_pos]
            
            # move moveRobot
            robotPositions[mr_idx] = (mx_next,my_next)
            robotsMoved           += [mr_idx]
            
            # update the discoMap
            for (x,y) in self._OneHopNeighborhood(mx_next,my_next):
                if   self.realMap[x][y] == 0:
                    self.discoMap[x][y]=0
                elif self.realMap[x][y] == 1:
                    self.discoMap[x][y]=1
        
        return (robotPositions,self.discoMap,self.rankMaps[self.startPos])
    
    def _numHigherRankAndUnexploredNeighbors(self,x,y,discoMap):
        numHigherRankNeighbors = 0
        numUnexploredNeighbors = 0
        rankMap = self.rankMaps[self.startPos] # shorthand
        for (nx,ny) in self._OneHopNeighborhood(x,y):
            if  (
                    discoMap[nx][ny]==1 and
                    rankMap[(nx,ny)]>rankMap[(x,y)]
                ):
                numHigherRankNeighbors += 1
            if discoMap[nx][ny]==-1:
                numUnexploredNeighbors += 1
        return (numHigherRankNeighbors,numUnexploredNeighbors)

#======== core simulator

'''
calculates steps taken from source to destination
'''

def singleExploration(scenarioName,realMap,startPos,NavAlgClass,numRobots):
    navAlg         = NavAlgClass(realMap,startPos,numRobots)
    robotPositions = [startPos]*numRobots
    kpis           = {
        'scenarioName': scenarioName,
        'navAlg':       NavAlgClass.__name__,
        'numTicks':     0,
        'numSteps':     0,
        'numRobots':    numRobots,
        'version':      '.'.join([str(n) for n in VERSION]),
    }
    
    while True:
        
        # think
        try:
            (nextRobotPositions,discoMap,rankMapStart)   = navAlg.think(robotPositions)
        except MappingDoneSuccess:
            kpis['mappingoutcome'] = 'success'
            break
        except MappingDoneIncomplete:
            kpis['mappingoutcome'] = 'incomplete'
            break
        
        # move
        for (i,(nx,ny)) in enumerate(nextRobotPositions):
            (cx,cy) = robotPositions[i]
            if (nx,ny)!= (cx,cy):
                kpis['numSteps'] += 1
            robotPositions[i] = nextRobotPositions[i]
        
        # update KPIs
        kpis['numTicks'] += 1
        
        # print
        if UI:
            printDiscoMap(discoMap,startPos,robotPositions,kpis)#,rankMapStart)
        
        #input()
    
    kpis['navStats'] = navAlg.getStats()
    
    return kpis

#============================ main ============================================

def main():

    numRobots      = NUM_ROBOTS
    NavAlgClasses  = [
        NavigationRama,
        NavigationAtlas,
        NavigationRandomWalk,
        NavigationBallistic,
    ]
    kpis           = []

    for scenarioName in SCENARIOS:
        
        # create the realMap
        (realMap,startPos) = genRealMapDrawing(getattr(AtlasScenarios,scenarioName))
        
        # execute the simulation for each navigation algorithm
        for NavAlgClass in NavAlgClasses:
            
            for r in range(NUMRUNS):
            
                # run single run
                start_time = time.time()
                kpis_run   = singleExploration(scenarioName,realMap,startPos,NavAlgClass,numRobots)
                print('run {0} in {1:.03f} s'.format(r,time.time()-start_time))
                
                # collect KPIs
                kpis      += [kpis_run]

    pp.pprint(kpis)
    print('Done.')

if __name__=='__main__':
    main()
    #cProfile.run('main()')