from queue import Queue
import random

class BBASim:
	def __init__(self, rates, chunkSec, bufSize, reservoirSize, cushionSize, capacity):
		self.rates = rates # Available video rates
		self.chunkSec = chunkSec # Number of seconds in a chunk
		self.bufSize = bufSize # Maximum number of seconds in buffer
		self.reservoirSize = max(reservoirSize, chunkSec) # How many seconds of video we should always have (use min rate if below)
		self.cushionSize = cushionSize # How many seconds of video we should have before hitting max rate
		self.capacity = capacity # Network capacity, C (bytes down)
		self.buffer = 0 # Number of seconds of video we have buffered
		self.rate = rates[0] # Current video rate
		self.rateQueue = Queue() # Keeps track of which rates of video have been downloaded
		self.partialChunkBytes = 0 # Number of bytes we've already downloaded of current chunk
		self.initialBufferComplete = False # Whether or not we have buffered the very first chunk of video
		self.log = ""

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
			if self.rateQueue.empty():
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

		if self.partialChunkBytes == 0:
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
			chunkRemaining = self.rate * self.chunkSec - self.partialChunkBytes
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
				self.partialChunkBytes = 0
				self.log += "----------------------\n"
				self.log += "Buffer remaining: " + str(bufRemaining) + "\n"
				self.log += "Capacity remaining: " + str(capacityRemaining) + "\n"
				self.log += "Chunk remaining: " + str(chunkRemaining) + "\n"
			# If we can't download a full single chunk, download as much as capacity and
			# remaining buffer allow and note how much of the chunk we downloaded
			bytesDown = min(capacityRemaining, bufRemaining * self.rate)
			self.buffer += bytesDown / self.rate
			self.partialChunkBytes += bytesDown
			self.log += "Couldn't finish chunk, downloaded " + str(self.partialChunkBytes) + "\n"
		else:
			self.log += "Buffer full, no download this cycle\n"

		self.log += "============================\n"
		self.log += "============================\n"
		return True


if __name__ == "__main__":
	rates = [400.0, 800.0, 1200.0, 1500.0, 4000.0, 8000.0]
	bufSizes = [5, 10, 50, 100, 240, 1000]
	chunkSecs = [1, 2, 3, 4, 5, 10]
	cushionFracs = [0.25, 0.5, 0.75, 0.9, 1.0]
	capacities = [400, 2000, 3000, 7000, 16000]
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
	# 					# if bufSize == 240 and chunkSec == 4 and cushionFrac == 0.9 and capacity == 3000 and reservoirFrac == 0.1:
	# 					# 	bbaSim.printLog()
						
	# Test with random capacities
	for bufSize in bufSizes:
		for chunkSec in chunkSecs:
			if chunkSec > bufSize:
				continue
			for cushionFrac in cushionFracs:
				for reservoirFrac in reservoirFracs:
					if reservoirFrac > cushionFrac:
						continue
					capacity = random.choice(capacities)
					bbaSim = BBASim(rates, chunkSec, bufSize, reservoirFrac * bufSize, cushionFrac * bufSize, capacity)
					for i in range(100):
						capacity = random.choice(capacities)
						success = bbaSim.simulateSecond(capacity)
						if not success:
							break
					#bbaSim.printLog()