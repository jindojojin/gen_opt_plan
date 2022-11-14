import math
import random
import time
from DBMS import DBMS
from common import BooleanExp, Predicate
columns = list(map(lambda i: f"c{i}", range(55)))
ops = [">", ">=", "<=", "<", "=", "!="]

maxValues = [2480, 174, 39, 283, 84, 272, 237, 243, 134, 892, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3]
minValues = [2442, 150, 25, 175, 56, 182, 223, 209, 65, 841, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3]


def genBxp(predicate_count: int, summand_size=2, type="dnf"):
    DNF = BooleanExp([], type)
    attrs = random.sample(columns, predicate_count)
    predicates = []
    for a in attrs:
        column_idx = int(a[1:])
        op = random.sample(ops, 1)[0]
        value = random.randint(
            minValues[column_idx], maxValues[column_idx])
        predicates.append(Predicate(a, op, value))
    for i in range(math.ceil(predicate_count/summand_size)):
        DNF.addGroup(predicates[i*summand_size:i*summand_size+summand_size])
    return DNF


if __name__ == "__main__":
    db = DBMS()
    for test in range(5): 
        bxp = genBxp(8, 3, "dnf")
        query = bxp.toString()
        print("TDSimMemo Plan:")
        startTime = time.time()
        tdsim_plan = db.genPlan(
            algorithm="TDSimMemo", query=query, queryType="dnf")
        db.showPlan(tdsim_plan)

        print("TDACB Plan:")
        acb_plan = db.genPlan(
            algorithm="TDACB", query=query, queryType="dnf")
        db.showPlan(acb_plan)
        print(bxp.toString())
        plan = db.genPlan('TDACB', bxp.toString(), bxp.expType)
        
        # print("Plan: ")
        # db.showPlan(plan)
        # result,cols = db.executePlan(plan)
        # print("Result :")
        # db.showResult(result,cols)


# dataFile = open("covtype.data", "r")
# for line in dataFile:
#     colValues = line[:-1].split(",")
#     for idx, colV in enumerate(colValues):
#         if (int(colV) > maxValues[idx]):
#             maxValues[idx] = int(colV)
#         if (int(colV) < minValues[idx]):
#             minValues[idx] = int(colV)
# print(maxValues)
# print(minValues)
