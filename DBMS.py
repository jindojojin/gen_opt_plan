import math
from tabulate import tabulate
from common import Predicate, Assignment, BooleanExp, Step, getAsgMemoKey, getBxpFromQueryStr, getPredicates


class DBMS:
    Memo = {}
    LBMemo = {}
    ACBMemo = {}
    RelationSize = 53
    _as = 3  # | => constants for scan operator
    _bs = 2  # |

    _ax = 2  # | => constants for map operator
    _bx = 1  # |

    def __init__(self):
        self.dataFile = open("covtype.data", "r")
        self.columns = list(map(lambda i: f"c{i}", range(54)))

    def scan(self):
        self.R = []
        Ridx = []
        for i, line in enumerate(self.dataFile):
            row = line[:-1].split(",")
            self.R.append(row)
            Ridx.append(i)
        return Ridx, []

    def getData(self, rowId: int, columnName: str):
        if (self.R == None):
            raise Exception("Not scaned")

        colIdx = -1
        for idx, col in enumerate(self.columns):
            if (col == columnName):
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
            if self.check(colData, predicate.op, predicate.value):
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
                    case 'map':
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
                    p_in_e, p_in_p = getXpe(step)
                    predicates_in_e += p_in_e
            return (predicates_in_e, []) if p.key in predicates_in_e else (predicates_in_e, [p.key])
        # Xp|e = Xp \ Xe // outstanding maps ;  Xe = ∪pj∈eXp
        Xe,Xpe = getXpe(e)

        if e == None:  # init plan :  e =  Scan(R)
            # σp(χ∗P (e))
            return [Step('map', columns=[p.key]), Step('select', p, branch=True)]
        elif branch == True:
            # σp(Xp|e(σ+pj(e)))
            return [Step('map', columns=Xpe), Step('select', p, branch=True)]
        elif branch == False:
            # σp(Xp|e(σ-pj(e)))
            return [Step('map', columns=Xpe), Step('select', p, branch=False)]
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
                    [Step('scan(R)')], [e0, eT, eF], []]
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
                        [Step('scan(R)')], [e0, eT, eF], []]
                    bestcost = cost
            self.Memo[key] = bestplan
            return bestplan

    def TDACB(self, e: list[Step], Bxp: BooleanExp, Asg: list[Assignment], branch: bool, b: int):
        memoKey = getAsgMemoKey(Asg)
        LB = self.LBMemo[memoKey] if memoKey in self.LBMemo else 0
        if memoKey in self.ACBMemo:
            plan = self.ACBMemo[memoKey]
            if (self.Cost(plan) <= b):
                return plan
        if LB >= b:
            return None
        if LB > 0:
            b = max(b, LB*2)
            return None
        bestcost = math.inf
        bestplan = None
        if b >= 0:
            for p in Bxp.getPredicates():
                e0 = self.BuildPlan(p, e, branch)
                b_ = min(b, bestcost) - self.Cost(e0)
                A = Assignment(p, True)
                eT = self.TDACB(e0, Bxp.applyAsg(A), Asg+[A], True, b_)
                if (eT != None):
                    b_ = b_ - self.Cost(eT)
                    A = Assignment(p, False)
                    eF = self.TDACB(e0, Bxp.applyAsg(A), Asg+[A], False, b_)
                    if (eF != None):
                        cost = self.Cost(e0) + self.Cost(eT) + self.Cost(eF)
                        if bestplan == None or bestcost > cost:
                            bestplan = [e0, eT, eF] if e else [
                                [Step('scan(R)')], [e0, eT, eF], []]
                            bestcost = cost
        if bestplan and len(bestplan) == 3 and (bestplan[1] == None or bestplan[2] == None):
            self.LBMemo[memoKey] = b
            return None
        self.ACBMemo[memoKey] = bestplan
        return self.ACBMemo[memoKey]

    def genPlan(self, algorithm: str, query: str, queryType="dnf"):
        Bxp = getBxpFromQueryStr(query, queryType)
        match algorithm:
            case "TDSim":
                self.bestPlan = self.TDSim(
                    e=None, Bxp=Bxp, Asg=[], branch=None)
            case "TDSimMemo":
                self.bestPlan = self.TDSimMemo(
                    e=None, Bxp=Bxp, Asg=[], branch=None)
            case "TDACB":
                self.bestPlan = self.TDACB(
                    e=None, Bxp=Bxp, Asg=[], branch=None, b=10e5)
        return self.bestPlan

    result = []  # For executePlan()

    def doSteps(self, steps: list[Step], prevResultT, prevResultF, level):
        resultT = []
        resultF = []
        columns = []
        indent = "      "*level
        for step in steps:
            # print("")
            # print(indent, "step = ", step.toString())
            # print(indent, "Input: ", "True:", prevResultT,
            #       " False:", prevResultF)
            match(step.action):
                case 'scan(R)':
                    resultT, resultF = self.scan()
                case 'map':
                    columns += step.columns
                    resultT, resultF = prevResultT, prevResultF
                case 'select':
                    # print(indent,
                    #       f'Select {step.predicate.alias} from {step.branch}: {prevResultT if step.branch else prevResultF}')
                    if (step.branch == True):
                        resultT, resultF = self.select(
                            prevResultT, step.predicate)
                    else:
                        resultT, resultF = self.select(
                            prevResultF, step.predicate)
            # print(indent, f"Output: True: {resultT}   False: {resultF}")
        return resultT, resultF, columns

    def executePlan(self, plan: list, prevResultT=None, prevResultF=None, level=0):
        result = []
        columns = []
        resultT, resultF, cols = self.doSteps(
            plan[0], prevResultT, prevResultF, level)
        columns += cols
        branch_count = 0
        for i in range(1, 3):
            if isinstance(plan[i], list) and len(plan[i]) > 0:
                branch_count += 1
                rowIds, colIds = self.executePlan(
                    plan[i], resultT, resultF, level+1)
                result += rowIds
                columns += colIds
        if (branch_count == 1):
            result += resultT if (plan[1] == None or len(plan[1]) == 0) else resultF
        if (branch_count == 0):
            result += resultT
        return result, list(set(columns))

    def showResult(self, rowIds: list[int], colKeys: list[str]):
        result = []
        for rid in rowIds:
            data = []
            for key in colKeys:
                data.append(self.getData(rid, key))
            result.append(data)
        print(tabulate(result, headers=colKeys, tablefmt="grid"))
        # return result

    def showPlan(self, plan, level=0):
        if (plan == None):
            return
        for step in plan:
            if isinstance(step, Step):
                print("   |"*level, step.toString())
            else:
                self.showPlan(step, level+1)


if __name__ == "__main__":
    DNFqueryStr = "(c0 > 2450 AND c1 >= 172) OR c2=28"

    db = DBMS()
    print("TDSimMemo Plan:")
    tdsim_plan = db.genPlan(
        algorithm="TDSimMemo", query=DNFqueryStr, queryType="dnf")
    db.showPlan(tdsim_plan)
    
    # print("TDACB Plan:")
    # acb_plan = db.genPlan(
    #     algorithm="TDACB", query=DNFqueryStr, queryType="dnf")
    # db.showPlan(acb_plan)

