import math
import random
import time

import tabulate
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


def get_Test_Summary(datas):
    print("test Data", datas)
    for alData in datas:
        minV = math.inf
        maxV = 0
        sum = 0
        for d in alData:
            sum += d
            minV = min(minV, d)
            maxV = max(maxV, d)
    return [round(minV,4), round(sum/len(datas),4),round( maxV,4)]


if __name__ == "__main__":
    db = DBMS()
    testResult = []
    for predicate_count in [4, 6, 8]:
        data = {
            'preds': predicate_count,
            'cnf': [],
            'dnf': []
        }
        for summand_size in range(2,3):
            for bxp_type in ["dnf"]:
                testDatas = []
                for test in range(5):
                    bxp = genBxp(predicate_count, summand_size, bxp_type)
                    query = bxp.toString()
                    testdata = []
                    for al in ["TDSimMemo"]:
                        # print(f"{al} Plan:")
                        startP = time.time()
                        best_plan = db.genPlan(
                            algorithm=al, query=query, queryType=bxp_type)
                        genP = time.time()
                        db.showPlan(best_plan)
                        rowIds, colIds = db.executePlan(best_plan)
                        # db.showResult(rowIds,colIds)
                        executeP = time.time()
                        testdata += [executeP-startP]
                    testDatas.append(testdata)
                data[bxp_type] += [{'summand_size': summand_size,
                                    'testDatas': get_Test_Summary(testDatas)}]
        testResult.append(data)
    table_data = []
    print(testResult)
    for s in testResult:
        row = [s['preds']]
        for bxptype in ['dnf','cnf']:
            for al in s[bxptype]:
                row+= al['testDatas']
        table_data.append(row)
    print(tabulate.tabulate(table_data, tablefmt="grid"))

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
