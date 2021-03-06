from queue import Queue
import random
import matplotlib.pyplot as plt

class BBASim:
	def __init__(self, rates, chunkSec, bufSize, reservoirSize, cushionSize, capacity):
		self.rates = rates # Available video rates (Mbps)
		self.chunkSec = chunkSec # Number of seconds in a chunk
		self.bufSize = bufSize # Maximum number of seconds in buffer
		self.reservoirSize = max(reservoirSize, chunkSec) # How many seconds of video we should always have (use min rate if below)
		self.cushionSize = cushionSize # How many seconds of video we should have before hitting max rate
		self.capacity = capacity # Network capacity, C (Mbps)
		self.buffer = 0 # Number of seconds of video we have buffered
		self.rate = rates[0] # Current video rate
		self.rateQueue = Queue() # Keeps track of which rates of video have been downloaded
		self.partialChunkMb = 0 # Number of Mb we've already downloaded of current chunk
		self.initialBufferComplete = False # Whether or not we have buffered the very first chunk of video
		self.log = ""
		self.bufferVals = [] # For graphing, list of all buffer values over time
		self.rateVals = [] # For graphing, list of all rate values over time
		self.capacityVals = [] # For graphing, list of all capacity values over time

	def __rateMap(self):
		if self.buffer <= self.reservoirSize:
			return self.rates[0]
		elif self.buffer >= self.cushionSize:
			return self.rates[-1]
		else: # linear between rmin and rmax
			percentCushion = (self.buffer - self.reservoirSize) / (self.cushionSize - self.reservoirSize)
			return self.rates[0] + (percentCushion * (self.rates[-1] - self.rates[0]))

	def __getNextRate(self):
		self.log += "Previous rate: " + str(self.rate) + "\n"
		ratePlus = self.rates[-1] if self.rate == self.rates[-1] else min([rate for rate in self.rates if rate > self.rate])
		rateMinus = self.rates[0] if self.rate == self.rates[0] else max([rate for rate in self.rates if rate < self.rate])
		rateSuggest = self.__rateMap()
		self.log += "Suggested rate: " + str(rateSuggest) + "\n"
		rateNext = self.rate
		if rateSuggest == self.rates[0] or rateSuggest == self.rates[-1]:
			rateNext = rateSuggest
		elif rateSuggest >= ratePlus:
			rateNext = max([rate for rate in self.rates if rate < rateSuggest])
		elif rateSuggest <= rateMinus:
			rateNext = min([rate for rate in self.rates if rate > rateSuggest])
		# Have to pick a "safe" rate, not "risky" (i.e. chunk must finish before buffer runs below reservoir)
		if self.buffer > self.reservoirSize and rateNext * self.chunkSec / rates[0] > self.buffer - self.reservoirSize:
			availableRates = [rate for rate in self.rates if rate * self.chunkSec / rates[0] <= self.buffer - self.reservoirSize]
			if not availableRates:
				rateNext = rates[0]
			else:
				rateNext = max(availableRates)
		# Custom addition: never return a (rate * chunk sec) greater than buffer size
		# if rateNext * self.chunkSec > self.bufSize:
		# 	availableRates = [rate for rate in self.rates if rate * self.chunkSec <= self.bufSize]
		# 	if not availableRates:
		# 		return -1
		# 	rateNext = max(availableRates)
		self.log += "New rate: " + str(rateNext) + "\n"
		return rateNext

	def printLog(self, error=None):
		if error:
			self.log += error
		self.log += "bufSize: " + str(self.bufSize) + "\n"
		self.log += "chunkSec: " + str(self.chunkSec) + "\n"
		self.log += "cushionFrac: " + str(self.cushionSize / self.bufSize) + "\n"
		self.log += "capacity: " + str(self.capacity) + "\n"
		self.log += "reservoirFrac: " + str(self.reservoirSize / self.bufSize) + "\n"
		self.log += "\n\n\n\n"
		print(self.log)

	def simulateSecond(self, capacity=None):
		# TODO: Currently only support integer chunkSec >= 1. Adding support for floats is nontrivial.
		# -----DRAIN-----
		self.log += "DRAIN\n"
		if self.initialBufferComplete:
			if self.buffer <= 0:
				error = "NO CHUNK FULLY DOWNLOADED!\n"
				self.printLog(error)
				return False
			drainRate = self.rateQueue.get(block=False)
			self.buffer -= 1

			if self.buffer < 0:
				error = "BUFFER RAN EMPTY!\n"
				self.printLog(error)
				return False
			self.log += "Drained rate: " + str(drainRate) + "\n"
		self.log += "Approx blocks in queue: " + str(self.rateQueue.qsize()) + "\n"
		self.log += "=======================================\n"


		# ----DOWNLOAD-----
		self.log += "DOWNLOAD\n"
		# If user supplied new capacity, update
		if capacity:
			self.capacity = capacity

		if self.partialChunkMb == 0:
			newRate = self.__getNextRate()
			if newRate < 0:
				error = "BUFFER TOO SMALL, NO SUITABLE RATE.\n"
				self.printLog(error)
				return False
			self.rate = newRate
		bufRemaining = self.bufSize - self.buffer
		self.log += "Buffer remaining: " + str(bufRemaining) + "\n"
		if bufRemaining > 0:
			capacityRemaining = self.capacity
			chunkRemaining = self.rate * self.chunkSec - self.partialChunkMb
			self.log += "Capacity remaining: " + str(capacityRemaining) + "\n"
			self.log += "Chunk remaining: " + str(chunkRemaining) + "\n"
			# If we can, download a full single chunk and reevaluate rate
			while bufRemaining >= chunkRemaining / self.rate and chunkRemaining <= capacityRemaining:
				self.log += "Finishing chunk\n"
				capacityRemaining -= chunkRemaining
				bufRemaining -= chunkRemaining / self.rate
				for _ in range(self.chunkSec):
					self.rateQueue.put(self.rate)
				self.buffer += chunkRemaining / self.rate
				self.initialBufferComplete = True
				if min(capacityRemaining, bufRemaining) > 0:
					newRate = self.__getNextRate()
					if newRate < 0:
						error = "BUFFER TOO SMALL, NO SUITABLE RATE.\n"
						self.printLog(error)
						return False
					self.rate = newRate
					chunkRemaining = self.rate * self.chunkSec
				self.partialChunkMb = 0
				self.log += "----------------------\n"
				self.log += "Buffer remaining: " + str(bufRemaining) + "\n"
				self.log += "Capacity remaining: " + str(capacityRemaining) + "\n"
				self.log += "Chunk remaining: " + str(chunkRemaining) + "\n"
			# If we can't download a full single chunk, download as much as capacity and
			# remaining buffer allow and note how much of the chunk we downloaded
			MbDown = min(capacityRemaining, bufRemaining * self.rate)
			self.buffer += MbDown / self.rate
			self.partialChunkMb += MbDown
			self.log += "Couldn't finish chunk, downloaded " + str(self.partialChunkMb) + "\n"
		else:
			self.log += "Buffer full, no download this cycle\n"

		self.log += "============================\n"
		self.log += "============================\n"
		self.bufferVals.append(self.buffer)
		self.rateVals.append(self.rate)
		self.capacityVals.append(self.capacity)
		return True

	def getGraphVals(self):
		return self.bufferVals, self.rateVals, self.capacityVals


if __name__ == "__main__":
	rates = [1, 2.5, 5, 8, 16, 45]
	bufSizes = [5, 10, 50, 100, 240, 1000]
	chunkSecs = [1, 2, 3, 4, 5, 10]
	cushionFracs = [0.25, 0.5, 0.75, 0.9, 1.0]
	capacities = [1, 2, 3, 5, 10, 30, 50]
	reservoirFracs = [0.1, 0.25, 0.5, 0.75, 1.0]
	# Test with fixed capacities
	ratePrev = rates[0]
	# for bufSize in bufSizes:
	# 	for chunkSec in chunkSecs:
	# 		if chunkSec > bufSize:
	# 			continue
	# 		for cushionFrac in cushionFracs:
	# 			for capacity in capacities:
	# 				for reservoirFrac in reservoirFracs:
	# 					if reservoirFrac > cushionFrac:
	# 						continue
	# 					bbaSim = BBASim(rates, chunkSec, bufSize, reservoirFrac * bufSize, cushionFrac * bufSize, capacity)
	# 					for i in range(100):
	# 						success = bbaSim.simulateSecond()
	# 						if not success:
	# 							break
						# if bufSize == 240 and chunkSec == 4 and cushionFrac == 0.9 and capacity == 5 and reservoirFrac == 0.1:
						# 	bbaSim.printLog()
						
	# Test with random capacities
	# for bufSize in bufSizes:
	# 	for chunkSec in chunkSecs:
	# 		if chunkSec > bufSize:
	# 			continue
	# 		for cushionFrac in cushionFracs:
	# 			for reservoirFrac in reservoirFracs:
	# 				if reservoirFrac > cushionFrac:
	# 					continue
	# 				capacity = random.choice(capacities)
	# 				bbaSim = BBASim(rates, chunkSec, bufSize, reservoirFrac * bufSize, cushionFrac * bufSize, capacity)
	# 				for i in range(100):
	# 					capacity = random.choice(capacities)
	# 					success = bbaSim.simulateSecond(capacity)
	# 					if not success:
	# 						break
	
	# Generate graphs
	fig, ax = plt.subplots()
	capacity = random.choice(capacities)
	capacityIndex = capacities.index(capacity)
	bbaSim = BBASim(rates, 4, 240, 0.25 * 240, 0.8 * 240, capacity)
	for i in range(200):
		availableIndexes = [capacityIndex]
		if capacityIndex > 0:
			availableIndexes.append(capacityIndex - 1)
		if capacityIndex < len(capacities) - 1:
			availableIndexes.append(capacityIndex + 1)
		capacityIndex = random.choice(availableIndexes)
		capacity = capacities[capacityIndex]
		success = bbaSim.simulateSecond(capacity)
		if not success:
			break
	bufferVals, rateVals, capacityVals = bbaSim.getGraphVals()
	xVals = [i for i in range(200)]
	reservoirVals = [0.25 * 240 for i in range(200)]
	cushionVals = [0.8 * 240 for i in range(200)]
	ax.plot(xVals, rateVals, label='Rate', color='b')
	ax.plot(xVals, capacityVals, label='Capacity', color='r')
	ax.set_ylabel('Mbps')
	ax.set_xlabel('Time (seconds)')
	ax.legend()
	fig.tight_layout()
	plt.grid(True)
	plt.savefig("RateCapacity.png")

	ax.clear()
	ax.plot(xVals, bufferVals, label='Buffer occupancy', color='g')
	ax.plot(xVals, reservoirVals, label='Reservoir', color='orange')
	ax.plot(xVals, cushionVals, label="Cushion", color="purple")
	ax.set_ylabel("Occupancy (seconds)")
	ax.set_xlabel("Time (seconds)")
	ax.legend()
	plt.ylim(0, 240)
	fig.tight_layout()
	plt.grid(True)
	plt.savefig("Buffer.png")