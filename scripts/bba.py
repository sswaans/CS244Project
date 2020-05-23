RATES = [400, 800, 1200, 1500, 4000, 8000] #kbps
CHUNK_SEC = 4
BUF_MAX_KB = 96000
RESERVOIR_KB = 90 * RATES[0]
CUSHION_KB = 0.9 * BUF_MAX_KB

def rateMap(bufNow):
	if bufNow <= RESERVOIR_KB:
		return RATES[0]
	elif bufNow >= CUSHION_KB:
		return RATES[-1]
	else: # linear between rmin and rmax
		percentCushion = (bufNow - RESERVOIR_KB) / (CUSHION_KB - RESERVOIR_KB)
		return RATES[0] + (percentCushion * (RATES[-1] - RATES[0]))

def getNextRate(ratePrev, bufNow):
	ratePlus = RATES[-1] if ratePrev == RATES[-1] else min([rate for rate in RATES if rate > ratePrev])
	rateMinus = RATES[0] if ratePrev == RATES[0] else max([rate for rate in RATES if rate < ratePrev])
	rateSuggest = rateMap(bufNow)
	print("suggested rate %s" % rateSuggest)
	rateNext = ratePrev
	if rateSuggest == RATES[0] or rateSuggest == RATES[-1]:
		rateNext = rateSuggest
	elif rateSuggest >= ratePlus:
		rateNext = max([rate for rate in RATES if rate < rateSuggest])
	elif rateSuggest <= rateMinus:
		rateNext = min([rate for rate in RATES if rate > rateSuggest])
	return rateNext

ratePrev = RATES[0]
for i in range(10):
	bufNow = 80000
	print("ratePrev: %s" % ratePrev)
	print("bufNow: %s" % bufNow)
	rateNext = getNextRate(ratePrev, bufNow)
	ratePrev = rateNext
	print("rateNext: %s" % rateNext)
	print("=================")

# TODO: Implement "full" buffer, implement notion of "seconds" passing (buffer fills/empties, network capacity constant for now)
