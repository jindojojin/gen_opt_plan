import re


class Predicate:
    def __init__(self, key: str, op: str, value: str):
        self.key = key
        self.op = op
        self.value = value
        self.alias = f"{key}{op}{value}"


class Step:
    def __init__(self, action: str, predicate: Predicate = None, columns: list[str] = [], branch=None):
        self.action = action
        self.predicate = predicate
        self.columns = columns
        self.branch = branch

    def toString(self):
        return f"{self.action} ({self.predicate.alias if self.predicate != None else ''}, {self.branch if self.branch != None else ''})"


class Assignment:
    def __init__(self, p: Predicate, v: bool):
        self.predicate = p
        self.value = v


class BooleanExp:
    def __init__(self, groups: list[list[Predicate]], expType: str) -> None:
        self.groups = groups
        self.expType = expType

    def getPredicates(self):
        result = set()
        for g in self.groups:
            for p in g:
                result.add(p)
        return list(result)

    def toString(self):
        strR = []
        outStr = " OR " if self.expType == "dnf" else " AND "
        inStr = " AND " if self.expType == "dnf" else " OR "
        for g in self.groups:
            strR += [f"({inStr.join(map(lambda x: x.alias, g))})"]
        return outStr.join(strR)

    def applyAsg(self, Asg: Assignment):
        groups: list[list[Predicate]] = []
        match self.expType:
            case 'dnf':
                for g in self.groups:
                    if Asg.predicate.alias in map(lambda p: p.alias, g):
                        if (Asg.value == True):
                            predicates = list(filter(
                                lambda x: x.alias != Asg.predicate.alias, g))
                            if(len(predicates) == 0): # group da bang true, khong can xet cac group khac nua
                                break
                        else:
                            predicates = []
                        groups.append(predicates)
                    else:
                        groups.append(g)

            case 'cnf':
                for g in self.groups:
                    if Asg.predicate.alias in map(lambda p: p.alias, g):
                        if (Asg.value == True):
                            predicates = []
                        else:
                            predicates = list(filter(
                                lambda x: x.alias != Asg.predicate.alias, g))
                    else:
                        groups.append(g)
        return BooleanExp(list(filter(lambda group: len(group) > 0, groups)), self.expType)


def getAsgMemoKey(Asgs: list[Assignment]) -> str:
    key = ""
    for asg in Asgs:
        key += f"{asg.predicate.alias}{asg.value}"
    return key


def getPredicates(Bxp: str) -> list[Predicate]:
    regex = r"([a-zA-Z0-9]+)\s*([><=!]+)\s*([a-zA-Z0-9]+)"
    matches = re.finditer(regex, Bxp, re.MULTILINE)
    result: list[Predicate] = []
    for match in matches:
        result.append(Predicate(match[1], match[2], match[3]))
    return result


def getBxpFromQueryStr(queryStr: str, queryType="dnf") -> BooleanExp:
    groups = []
    match queryType:
        case "dnf":
            groupsRaw = queryStr.split("OR")
            for g in groupsRaw:
                groups.append(getPredicates(g))
        case "cnf":
            groupsRaw = queryStr.split("AND")
            for g in groupsRaw:
                groups.append(getPredicates(g))
    return BooleanExp(groups, queryType)


if __name__ == "__main__":
    DNFqueryStr = "(c > 0 AND l > 0) OR (r > 0)"
    CNFqueryStr = "(a > 0) AND (a > 0 OR b=0) AND c != 3 AND (d = 4 OR e <= 3)"

    b1 = getBxpFromQueryStr(DNFqueryStr, 'dnf')
    b2 = b1.applyAsg(Assignment(Predicate('c', '>', '0'), True))

    print(b2.toString())
    print(b2.applyAsg(Assignment(Predicate('l', '>', '0'), True)).toString())
    # print(b2.applyAsg(Assignment(Predicate('a', '>', '0'), True)).toString())
