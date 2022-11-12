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
        self.R = self.scan()
        # print(self.R)

    def scan(self):
        result = []
        for line in self.dataFile:
            data = line[:-1].split(",")
            row = []
            idx = 0
            for col in self.collumns:
                row.append(data[int(idx): int(idx + col[1])])
                idx += col[1]
            result.append(row)
        return result

    def select(self, data, columns=["Elevation", "Aspect", "Slope"], where: Predicate = None, bypass=True):
        p: Predicate = where
        result = []
        F_result = []  # false result for bypass
        rawColumns = [column[0] for column in self.collumns]
        columns = columns if len(columns) > 0 else rawColumns
        for r in data:
            row = []
            is_ok = True
            for col in columns:
                col_idx = rawColumns.index(col)
                col_data = r[col_idx]
                # where handle
                if(col == p.key and not self.check(col_data[0], p.op, p.value)):
                    is_ok = False
                    break
                row.append(r[col_idx])
            if (is_ok):
                result.append(row)
            elif (bypass):
                F_result.append(row)
        return (result, F_result)

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
        if(e == None):
            return 0
        cost = 0
        for step in e:
            if(isinstance(step, Step)):
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
            predicates_in_e = []
            for step in plan:
                if(isinstance(step, Step)):
                    if(step.predicate and step.predicate.key not in predicates_in_e):
                        predicates_in_e.append(step.predicate.key)
                elif isinstance(step, list):
                    predicates_in_e += getXpe(step)[0]
            return (predicates_in_e, []) if p.key in predicates_in_e else (predicates_in_e, [p.key])
        # Xp|e = Xp \ Xe // outstanding maps ;  Xe = ∪pj∈eXp
        Xp, Xpe = getXpe(e)

        if len(e) == 1 and e[0].action == 'scan(R)':
            return e + [Step('select', p)]  # σp(χ∗P (e))
        elif branch == True:
            return [Step('select', p, branch=True)]  # σp(Xp|e(σ+pj(e)))
        elif branch == False:
            return [Step('select', p, branch=False)]  # σp(Xp|e(σ-pj(e)))
        return e

    def TDSim(self, e: list[Step], Bxp: BooleanExp, Asg: list[Assignment], branch: bool):
        bestcost = 10e60
        bestplan = None
        # print("predicates ",list(map(lambda p: p.alias,Bxp.getPredicates())))
        bestPlans = []
        for p in Bxp.getPredicates():
            e0 = self.BuildPlan(p, e, branch)
            A = Assignment(p, True)
            eT = self.TDSim(e0, Bxp.applyAsg(A), Asg + [A], True)[0]
            A = Assignment(p, False)
            eF = self.TDSim(e0, Bxp.applyAsg(A), Asg + [A], False)[0]
            cost = self.Cost(eT) + self.Cost(eF) + self.Cost(e0)
            bestPlans.append([e0, eT, eF])
            if (bestplan == None or bestcost > cost):
                bestplan = [e0, eT, eF]
                bestcost = cost
        return bestplan, bestPlans

    def TDSimMemo(self, e: list[Step], Bxp: BooleanExp, Asg: list[Assignment], branch: bool):
        key = getAsgMemoKey(Asg)
        if key in self.Memo:
            return self.Memo
        else:
            bestplan = self.TDSim(e, Bxp, Asg, branch)
            self.Memo[key] = bestplan
            return bestplan

    def genPlan(self, algorithm: str, query: str, queryType="dnf"):
        Bxp = getBxpFromQueryStr(query, queryType)
        print(list(map(lambda p: p.alias, Bxp.getPredicates())))
        match algorithm:
            case "TDSim":
                self.bestPlan = self.TDSim(
                    e=[Step('scan(R)')], Bxp=Bxp, Asg=[], branch=None)
        return self.bestPlan

    result = []  # For executePlan()

    # def executePlan(self, plan=None, prevResultT=None, prevResultF=None, parent=None):
    #     if(plan == None):
    #         plan = self.bestPlan
    #     if(prevResultT == None):
    #         prevResultT = self.R
    #     if(prevResultF == None):
    #         prevResultF = self.R
    #     resultT = []
    #     resultF = []
    #     for step in plan:
    #         if(isinstance(step, Step)):
    #             match(step.action):
    #                 case 'select':
    #                     if(step.branch == True):
    #                         resultT, resultF = self.select(
    #                             data=prevResultT, where=step.predicate)
    #                     elif (step.branch == False):
    #                         resultT, resultF = self.select(
    #                             data=prevResultF, where=step.predicate)
    #                     else:  # None
    #                         resultT, resultF = self.select(
    #                             data=self.R, where=step.predicate)

    #                     if(parent != None and len(parent) > 1 and (parent[-1] == None or parent[-2] == None)):
    #                         print(step.predicate.alias)
    #                         print("True:", len(resultT))
    #                         print("False:", len(resultF))
    #                         self.result += resultT
    #         elif isinstance(step, list):
    #             self.executePlan(step, resultT, resultF, plan)

    def getResult(self):
        return self.result

    def showPlan(self, plan, level=0, parent=None):
        if(plan == None):
            return
        for step in plan:
            if isinstance(step, Step):
                print("   "*level, step.toString())
                # if(len(parent) > 1 and (parent[-1] == None or parent[-2] == None)):
            else:
                self.showPlan(step, level+1, plan)


if __name__ == "__main__":
    DNFqueryStr = "(Elevation > 2450 AND Aspect >= 172) OR Slope=28"

    db = DBMS()
    dnf_plan, plans = db.genPlan(
        algorithm="TDSim", query=DNFqueryStr, queryType="dnf")
    db.showPlan(dnf_plan)
    # db.executePlan()
    # print(db.getResult())
    # for p in plans:
    #     print("+"*20)
    #     db.showPlan(p)
# print([1,2,3,4][1:2])
