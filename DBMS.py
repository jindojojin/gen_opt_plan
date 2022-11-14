import math
from common import Predicate, Assignment, BooleanExp, Step, getAsgMemoKey, getBxpFromQueryStr, getPredicates


class DBMS:
    Memo = {}
    AsgMap = {}  # maping "hash of Asg" to Asg

    RelationSize = 53
    _as = 3  # | => constants for scan operator
    _bs = 2  # |

    _ax = 2  # | => constants for map operator
    _bx = 1  # |

    def __init__(self):
        self.dataFile = open("covtype.data", "r")
        self.collumns = [  # Forest Data only
            ["Elevation", 1],
            ["Aspect", 1],
            ["Slope", 1],
            ["Horizontal_Distance_To_Hydrology", 1],
            ["Vertical_Distance_To_Hydrology", 1],
            ["Horizontal_Distance_To_Roadways", 1],
            ["Hillshade_9am", 1],
            ["Hillshade_Noon", 1],
            ["Hillshade_3pm", 1],
            ["Horizontal_Distance_To_Fire_Points", 1],
            ["Wilderness_Area", 4],
            ["Soil_Type", 40],
            ["Cover_Type", 1]
        ]
        # self.R = self.scan()
        # print(self.R)

    def scan(self):
        self.R = []
        Ridx = []
        for i, line in enumerate(self.dataFile):
            data = line[:-1].split(",")
            row = []
            idx = 0
            for col in self.collumns:
                row.append(data[int(idx): int(idx + col[1])])
                idx += col[1]
            self.R.append(row)
            Ridx.append(i)
        return Ridx, []

    def getData(self, rowId: int, columnName: str):
        if (self.R == None):
            raise Exception("Not scaned")

        colIdx = -1
        for idx, col in enumerate(self.collumns):
            if (col[0] == columnName):
                colIdx = idx
        if (colIdx == -1):
            raise Exception("invalid column")
        return self.R[rowId][colIdx]

    def select(self, rowIds: list[int], predicate: Predicate = None):
        if (rowIds == None):
            return [], []
        resultT = []
        resultF = []
        for rowId in rowIds:
            colData = self.getData(rowId, predicate.key)
            if self.check(colData[0], predicate.op, predicate.value):
                resultT.append(rowId)
            else:
                resultF.append(rowId)
        return resultT, resultF

    def check(self, v1, operator, v2):
        match operator:
            case '=':
                return v1 == v2
            case '!=':
                return int(v1) != int(v2)
            case '<=':
                return int(v1) <= int(v2)
            case '<':
                return int(v1) < int(v2)
            case '>=':
                return int(v1) >= int(v2)
            case '>':
                return int(v1) > int(v2)

    def Cost(self, e: list[Step]):
        if (e == None):
            return 0
        cost = 0
        for step in e:
            if (isinstance(step, Step)):
                match step.action:
                    case 'scan(R)':
                        cost += self.RelationSize * self._as + self._bs
                    case 'X*(A)':
                        cost += len(step.columns) * self._ax + self._bx
                    case 'select':
                        cost += len(step.columns)
            else:
                cost += self.Cost(step)
        return cost

    def BuildPlan(self, p: Predicate, e: list[Step], branch: bool):
        def getXpe(plan):
            if (plan == None):
                return ([], [])
            predicates_in_e = []
            for step in plan:
                if (isinstance(step, Step)):
                    if (step.predicate and step.predicate.key not in predicates_in_e):
                        predicates_in_e.append(step.predicate.key)
                elif isinstance(step, list):
                    predicates_in_e += getXpe(step)[0]
            return (predicates_in_e, []) if p.key in predicates_in_e else (predicates_in_e, [p.key])
        # Xp|e = Xp \ Xe // outstanding maps ;  Xe = ∪pj∈eXp
        Xp, Xpe = getXpe(e)

        if e == None:  # init plan :  e =  Scan(R)
            return [Step('select', p, branch=True)]  # σp(χ∗P (e))
        elif branch == True:
            return [Step('select', p, branch=True)]  # σp(Xp|e(σ+pj(e)))
        elif branch == False:
            return [Step('select', p, branch=False)]  # σp(Xp|e(σ-pj(e)))
        return e

    def TDSim(self, e: list[Step], Bxp: BooleanExp, Asg: list[Assignment], branch: bool):
        bestcost = math.inf
        bestplan = None
        # print("predicates ",list(map(lambda p: p.alias,Bxp.getPredicates())))
        for p in Bxp.getPredicates():
            e0 = self.BuildPlan(p, e, branch)
            A = Assignment(p, True)
            eT = self.TDSim(e0, Bxp.applyAsg(A), Asg + [A], True)
            A = Assignment(p, False)
            eF = self.TDSim(e0, Bxp.applyAsg(A), Asg + [A], False)
            cost = self.Cost(eT) + self.Cost(eF) + self.Cost(e0)
            if (bestplan == None or bestcost > cost):
                bestplan = [e0, eT, eF] if e else [
                    [Step('scan(R)')], [e0, eT, eF], None]
                bestcost = cost
        return bestplan

    def TDSimMemo(self, e: list[Step], Bxp: BooleanExp, Asg: list[Assignment], branch: bool):
        key = getAsgMemoKey(Asg)
        if key in self.Memo:
            return self.Memo[key]
        else:
            bestcost = math.inf
            bestplan = None
            for p in Bxp.getPredicates():
                e0 = self.BuildPlan(p, e, branch)
                A = Assignment(p, True)
                eT = self.TDSimMemo(e0, Bxp.applyAsg(A), Asg + [A], True)
                A = Assignment(p, False)
                eF = self.TDSimMemo(e0, Bxp.applyAsg(A), Asg + [A], False)
                cost = self.Cost(eT) + self.Cost(eF) + self.Cost(e0)
                if (bestplan == None or bestcost > cost):
                    bestplan = [e0, eT, eF] if e else [
                        [Step('scan(R)')], [e0, eT, eF], None]
                    bestcost = cost
            self.Memo[key] = bestplan
            return bestplan

    def genPlan(self, algorithm: str, query: str, queryType="dnf"):
        Bxp = getBxpFromQueryStr(query, queryType)
        print(list(map(lambda p: p.alias, Bxp.getPredicates())))
        match algorithm:
            case "TDSim":
                self.bestPlan = self.TDSim(
                    e=None, Bxp=Bxp, Asg=[], branch=None)
            case "TDSimMemo":
                self.bestPlan = self.TDSimMemo(
                    e=None, Bxp=Bxp, Asg=[], branch=None)
        return self.bestPlan

    result = []  # For executePlan()

    def doSteps(self, steps: list[Step], prevResultT, prevResultF, level):
        resultT = []
        resultF = []
        indent = "      "*level
        for step in steps:
            print("")
            print(indent, "step = ", step.toString())
            print(indent, "Input: ", "True:", prevResultT,
                  " False:", prevResultF)
            match(step.action):
                case 'scan(R)':
                    resultT, resultF = self.scan()
                case 'select':
                    print(indent,
                          f'Select {step.predicate.alias} from {step.branch}: {prevResultT if step.branch else prevResultF}')
                    if (step.branch == True):
                        resultT, resultF = self.select(
                            prevResultT, step.predicate)
                    else:
                        resultT, resultF = self.select(
                            prevResultF, step.predicate)
            print(indent, f"Output: True:{resultT}   False:{resultF}")
        return resultT, resultF

    def executePlan(self, plan: list, prevResultT=None, prevResultF=None, level=0):
        resultT, resultF = self.doSteps(
            plan[0], prevResultT, prevResultF, level)
        branch_count=0
        for i in range(1,3):
            if isinstance(plan[i], list):
                branch_count+=1
                self.executePlan(plan[i], resultT, resultF, level+1)
        if(branch_count == 1):
            self.result += resultT if plan[1] == None else resultF
        if(branch_count == 0):
            self.result += resultT        
        


    def getResult(self):
        return self.result

    def showPlan(self, plan, level=0):
        if (plan == None):
            return
        for step in plan:
            if isinstance(step, Step):
                print("   "*level, step.toString())
            else:
                self.showPlan(step, level+1)


if __name__ == "__main__":
    DNFqueryStr = "(Elevation > 2450 AND Aspect >= 172) OR (Elevation > 2450 AND Aspect >= 172) OR Slope=28"

    db = DBMS()
    dnf_plan = db.genPlan(
        algorithm="TDSimMemo", query=DNFqueryStr, queryType="dnf")
    # db.showPlan(dnf_plan)
    # print(dnf_plan)
    db.executePlan(db.bestPlan)
    print(db.getResult())
    # for p in plans:
    #     print("+"*20)
    #     db.showPlan(p)
# print([1,2,3,4][1:2])
