from PaperTrading import *

pt = PaperTrading("./trading/data", logging_level=logging.DEBUG)

print(pt.getPortfolio())