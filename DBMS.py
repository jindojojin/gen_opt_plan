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

    def select(self, columns=[], where: Predicate = None, bypass=False):
        p: Predicate = where
        result = []
        F_result = []  # false result for bypass
        rawColumns = [column[0] for column in self.collumns]
        columns = columns if len(columns) > 0 else rawColumns
        rawData = self.scan()
        for r in rawData:
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
        return (columns, result, F_result)

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

    def print(self, result):
        print(result[0])
        for r in result[1]:
            print(r)

    def Cost(self, e: list[Step]):
        cost = 0
        for step in e:
            match step.action:
                case 'scan(R)':
                    cost += self.RelationSize * self._as + self._bs
                case 'X*(A)':
                    cost += len(step.columns) * self._ax + self._bx
                case 'select':
                    cost += len(step.columns)

    def BuildPlan(self, p: Predicate, e: list[Step], branch: bool):
        def getXpe():
            predicates_in_e = []
            for step in e:
                if(step.predicate.key not in predicates_in_e):
                    predicates_in_e.append(step.predicate.key)
            return () if p.key in predicates_in_e else (p.key)
        Xpe = getXpe()  # Xp|e = Xp \ Xe // outstanding maps ;  Xe = ∪pj∈eXp

        if len(e) == 1 and e[0].action == 'scan(R)':
            e += [Step('select', p)]  # σp(χ∗P (e))
        elif branch == True:
            e += [Step('map', Xpe, branch=True),
                  Step('select', p)]  # σp(Xp|e(σ+pj(e)))
        else:
            e += [Step('map', Xpe, branch=False),
                  Step('select', p)]  # σp(Xp|e(σ-pj(e)))
        return e

    def TDSim(self, e: list[Step], Bxp: BooleanExp, Asg: list[Assignment], branch: bool):
        bestcost = 10e23
        bestplan = None
        for p in Bxp.getPredicates():
            e0 = self.BuildPlan(p, e, branch)
            A = Assignment(p, True)
            eT = self.TDSim(e0, Bxp.applyAsg(A), Asg + [A], True)
            A = Assignment(p, False)
            eF = self.TDSim(e0, Bxp.applyAsg(A), Asg + [A], False)
            cost = self.Cost(eT) + self.Cost(eF) + self.Cost(e0)
            if (bestplan == None or bestcost > cost):
                bestplan = e0 + eT + eF
                bestcost = cost
        return bestplan

    def TDSimMemo(self, e: list[Step], Bxp: BooleanExp, Asg: list[Assignment], branch: bool):
        key = self.getAsgMemoKey(Asg)
        if key in self.Memo:
            return self.Memo
        else:
            bestplan = self.TDSim(e, Bxp, Asg, branch)
            self.Memo[key] = bestplan
            return bestplan

    def genPlan(algorithm: str, query: str, queryType="dnf"):
        Bxp = getBxpFromQueryStr(query, queryType)
        match algorithm:
            case 'TDSim':
                return 0


db = DBMS()
dnf_plan = db.DNF_Plan(["Cover_Type", "Slope", "Aspect"],
                       "(Slope > 23 AND Aspect = 3) OR Elevation = 1", type="dnf")
db.print(dnf_plan)
# print([1,2,3,4][1:2])
