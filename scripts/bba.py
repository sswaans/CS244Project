from queue import Queue

class BBASim:
	def __init__(self, rates, chunkSec, bufSize, reservoirSize, cushionSize, capacity):
		self.rates = rates
		self.chunkSec = chunkSec
		self.bufSize = bufSize
		self.reservoirSize = reservoirSize # How many bytes of video we should always have (use min rate if below)
		self.cushionSize = cushionSize # How many bytes of video we should have before hitting max rate
		self.capacity = capacity # Network capacity, C (bytes down)
		self.buffer = 0
		self.rate = rates[0]
		self.rateQueue = Queue()
		self.partialChunkBytes = 0 # Number of bytes we've already downloaded of current chunk

	def __rateMap(self):
		if self.buffer <= self.reservoirSize:
			return self.rates[0]
		elif self.buffer >= self.cushionSize:
			return self.rates[-1]
		else: # linear between rmin and rmax
			percentCushion = (self.buffer - self.reservoirSize) / (self.cushionSize - self.reservoirSize)
			return self.rates[0] + (percentCushion * (self.rates[-1] - self.rates[0]))

	def __getNextRate(self):
		print("Previous rate: %s" % self.rate)
		ratePlus = self.rates[-1] if self.rate == self.rates[-1] else min([rate for rate in self.rates if rate > self.rate])
		rateMinus = self.rates[0] if self.rate == self.rates[0] else max([rate for rate in self.rates if rate < self.rate])
		rateSuggest = self.__rateMap()
		print("Suggested rate: %s" % rateSuggest)
		rateNext = self.rate
		if rateSuggest == self.rates[0] or rateSuggest == self.rates[-1]:
			rateNext = rateSuggest
		elif rateSuggest >= ratePlus:
			rateNext = max([rate for rate in self.rates if rate < rateSuggest])
		elif rateSuggest <= rateMinus:
			rateNext = min([rate for rate in self.rates if rate > rateSuggest])
		print("New rate: %s" % rateNext)
		return rateNext

	def simulateSecond(self):
		# TODO: Does it matter that we do all of our downloads before all of our drain?
		# TODO: Incorporate chunk sec (assuming 1 sec chunks right now)
		# ----DOWNLOAD-----
		print("DOWNLOAD")
		if self.partialChunkBytes == 0:
			self.rate = self.__getNextRate()
		bufRemaining = self.bufSize - self.buffer
		print("bufRemaining: %s" % bufRemaining)
		if bufRemaining > 0:
			capacityRemaining = self.capacity
			chunkRemaining = self.rate - self.partialChunkBytes
			print("Capacity remaining: %s" % capacityRemaining)
			print("Chunk remaining: %s" % chunkRemaining)
			# If we can, download a full single chunk and reevaluate rate
			while bufRemaining >= chunkRemaining and chunkRemaining <= capacityRemaining:
				print("Finishing chunk")
				self.buffer += chunkRemaining
				capacityRemaining -= chunkRemaining
				bufRemaining -= chunkRemaining
				self.rateQueue.put(self.rate)
				self.rate = self.__getNextRate()
				chunkRemaining = self.rate
				self.partialChunkBytes = 0
				print("----------------------")
				print("bufRemaining: %s" % bufRemaining)
				print("Capacity remaining: %s" % capacityRemaining)
				print("Chunk remaining: %s" % chunkRemaining)
			# If we can't download a full single chunk, download as much as capacity and
			# remaining buffer allow and note how much of the chunk we downloaded
			self.buffer += min(capacityRemaining, bufRemaining)
			self.partialChunkBytes += min(capacityRemaining, bufRemaining)
			print("Couldn't finish chunk, downloaded %s" % self.partialChunkBytes)
		else:
			print("Buffer full, no download this cycle")

		print("============================")
		# -----DRAIN-----
		print("DRAIN")
		self.buffer -= self.rateQueue.get()
		if self.buffer < 0:
			print("BUFFER RAN EMPTY!")
			exit()
		print("Drained buffer: %s" % self.buffer)
		print("Approx blocks in queue: %s" % self.rateQueue.qsize())
		print("=======================================")
		print("=======================================")


if __name__ == "__main__":
	rates = [400, 800, 1200, 1500, 4000, 8000]
	bufSize = 96000
	bbaSim = BBASim(rates, 4, 96000, 1 * rates[0], 0.9 * bufSize, 7000)
	ratePrev = rates[0]
	for i in range(1000):
		rateNext = bbaSim.simulateSecond()