# The MIT License (MIT)
# 
# Copyright (c) 2014 Joseph Cloutier
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import random
import argparse
import enum
from enum import Enum, unique
import sys
import time

parser = argparse.ArgumentParser(formatter_class=argparse.MetavarTypeHelpFormatter,
								usage="python " + sys.argv[0] + " -a 3 -m 2 "
									+ "(Simulates a 3x attack dice plus a x1-2 multiplier dice.)\n"
									+ "usage: python " + sys.argv[0] + " -a 6 2 -r 5 "
									+ "(Simulates 6x and 2x attack dice, stopping after rolling the 6x dice for the third time.)\n"
									+ "usage: python " + sys.argv[0] + " -p 1 -r 0 -d 20 "
									+ "(Simulates a regular poison dice, stopping only after reaching 20 damage.)",
								epilog="Note: Partial matches are accepted. For instance, "
									+ "you can type --attack instead of --attack_dice.")
parser.add_argument("--attack_dice", "-a", type=int, nargs="*", action="append",
					help="The attack dice to be rolled. The integer value indicates "
						+ "the amount the damage will be multiplied by. For instance, "
						+ "2 indicates an attack x2 dice.",
					dest="attack_dice")
parser.add_argument("--poison_dice", "-p", type=int, nargs="*", action="append",
					help="The poison dice to be rolled. The integer value indicates "
						+ "the amount the poison will be multiplied by. For instance, "
						+ "2 indicates a poison x2 dice.",
					dest="poison_dice")
parser.add_argument("--health_dice", type=int, nargs="*", action="append",
					help="The health dice to be rolled. The integer value indicates "
						+ "the amount the health will be multiplied by. For instance, "
						+ "2 indicates a heal x2 dice. Note: health dice are assumed "
						+ "to combo just like other types of dice, though I haven't "
						+ "checked this in-game.",
					dest="health_dice")
parser.add_argument("--multiplier_dice", "-m", type=int, nargs="*", action="append",
					help="The multiplier dice to be rolled. The integer value "
						+ "indicates the upper end of the range. For instance, a"
						+ "value of 2 indicates a 1-2 multiplier dice.",
					dest="multiplier_dice")
parser.add_argument("--greater_than_dice", "-g", type=int, nargs="*", action="append",
					help="The \">\" dice to be rolled. For instance, a value of "
						+ "1 indicates an attack > 1 dice. Note: > dice are assumed not to "
						+ "combo, though I haven't checked this in-game.",
					dest="greater_than_dice")
parser.add_argument("--golden_dice", type=int, nargs="*", action="append",
					help="The multiplier-greater-than dice to be rolled. The integer "
						+ "value indicates the value below the low end of the range. "
						+ "For instance, a value of 2 indicates a 3-6 multiplier dice. "
						+ "Note: This ought to be --multiplier_greater_than_dice, "
						+ "but then it would be unclear whether \"--multiplier\" "
						+ "referred to this or --multiplier_dice.",
					dest="multiplier_greater_than_dice")
parser.add_argument("--rolls_per_turn", "-r",
					default=6, type=int,
					help="End the turn after this many risky rolls. "
						+ "If this is 0, the turn will not end based on rolls.",
					dest="rolls")
parser.add_argument("--damage_threshold", "-d",
					default=0, type=int,
					help="End the turn after building up this much damage."
						+ "If this is 0, the turn will not end based on damage.",
					dest="threshold")
parser.add_argument("--turns", "-t", default=10000, type=int,
					help="The total number of turns to be run.",
					dest="turns")
parser.add_argument("--print_turns", action="store_true",
					help="Prints the results of each turn. Caution: Lots of text.",
					dest="print_turns")
parser.add_argument("--print_rolls", action="store_true",
					help="Prints the value of every single roll. Caution: Lots of text.",
					dest="print_rolls")
parser.add_argument("--print_combos", action="store_true",
					help="Displays a message whenever any combo is rolled. Caution: Lots of text.",
					dest="print_combos")
parser.add_argument("--print_triples", action="store_true",
					help="Displays a message whenever a triple or quadruple combo is rolled.",
					dest="print_triples")
parser.add_argument("--print_quadruples", action="store_true",
					help="Displays a message whenever a quadruple combo is rolled.",
					dest="print_quadruples")
args = parser.parse_args()

def flatten(list):
	if list == None:
		return None
	
	return [item for sublist in list for item in sublist]
args.attack_dice = flatten(args.attack_dice)
args.poison_dice = flatten(args.poison_dice)
args.health_dice = flatten(args.health_dice)
args.multiplier_dice = flatten(args.multiplier_dice)
args.greater_than_dice = flatten(args.greater_than_dice)
args.multiplier_greater_than_dice = flatten(args.multiplier_greater_than_dice)

@enum.unique
class DamageType(Enum):
	attack = 1
	poison = 2
	health = 3

class RollResult:
	def __init__(self):
		self.damage = {damageType:0 for damageType in DamageType.__members__}
		self.failed = False
		self.combos = {2:0, 3:0, 4:0}
	
	def add(self, other):
		for damageType in DamageType.__members__:
			self.damage[damageType] += other.damage[damageType]
		for i in range(2, 5):
			self.combos[i] += other.combos[i]
	
	def totalDamage(self):
		total = 0
		for damageType in DamageType.__members__:
			total += self.damage[damageType]
		return total
	
	def setFailed(self):
		self.failed = True
		for damageType in DamageType.__members__:
			self.damage[damageType] = 0
		#Don't clean up the combos.
	
	def __str__(self):
		result = ""
		if self.failed:
			result = "Failed turn"
		else:
			for damageType in DamageType.__members__:
				if self.damage[damageType] == 0:
					continue
				if len(result) > 0:
					result += ", "
				result += str(self.damage[damageType]) + " " + damageType
			
			if len(result) == 0:
				result = "No damage"
		
		#Append the combo string only if at least one combo was made.
		for combo in self.combos:
			if self.combos[combo] > 0:
				return result + ", " + self.combosToString()
		
		return result
	
	def combosToString(self):
		result = ""
		
		combosMade = 0
		for combo in self.combos:
			if self.combos[combo] > 0:
				combosMade += 1
		
		for combo in self.combos:
			if self.combos[combo] == 0:
				continue
			if len(result) > 0:
				result += ", "
			
			#If only one combo was made, don't print the number.
			if combosMade >= 1 or self.combos[combo] > 1:
				result += str(self.combos[combo]) + " "
			
			if combo == 2:
				result += "double combo"
			elif combo == 3:
				result += "triple combo"
			else:
				result += "quadruple combo"
			
			if self.combos[combo] > 1:
				result += "s"
		
		if len(result) == 0:
			result = "No combos made."
		
		return result

class Dice:
	"""Represents a single dice."""
	
	def __init__(self, minValue=1, maxValue=6, valueMultiplier=1, isMultiplierDice=False, damageType=DamageType.attack):
		if minValue > maxValue:
			print("Got a minimum value below the maximum value!")
			sys.exit(1)
		
		self.values = range(minValue, maxValue + 1)
		if len(self.values) > 6:
			print("Six-sided dice only! Got " + str(len(self.values)) + " sides.")
			sys.exit(1)
		
		self.valueMultiplier = valueMultiplier
		self.isMultiplierDice = isMultiplierDice
		self.damageType = damageType
		
		self.comboApplied = False
		self.notRolled = False
		self.failed = False
		self.currentRoll = 0
	
	def isRisky(self):
		return not self.isMultiplierDice \
				and self.damageType != DamageType.health \
				and self.values[0] == 1
	
	def roll(self):
		"""Step one: Roll this dice."""
		result = random.choice(self.values)
		if self.isRisky():
			self.failed = result == 1
		self.currentRoll = result * self.valueMultiplier
		
		if args.print_rolls:
			print(str(self) + " rolled a " + str(result)
				+ (" (Attack failed!)" if self.failed else ""))
		
		self.comboApplied = False
		self.notRolled = False
	
	def doNotRoll(self):
		"""Alternate step one: Choose not to roll this dice."""
		if self.isMultiplierDice:
			self.currentRoll = 1
		else:
			self.currentRoll = 0
		self.failed = False
		
		self.notRolled = True
	
	def applyRoll(self, rolledDice, rollResult):
		"""Step two: Apply the result of this roll to the other dice that were
		rolled. This applies regular multipliers and combo multipliers. Does
		not change the roll result except to record combos."""
		if self.notRolled or self.failed:
			return
		
		if not self.comboApplied:
			combo = [self]
			for other in rolledDice:
				if other == self or not self.combosWith(other) or other.notRolled:
					continue
				
				if other.currentRoll == self.currentRoll:
					combo.append(other)
			
			if len(combo) > 1:
				multiplier = self.comboValue(len(combo))
				
				initialRoll = self.currentRoll
				
				for dice in combo:
					dice.currentRoll *= multiplier
					dice.comboApplied = True
				
				rollResult.combos[len(combo)] += 1
				
				if args.print_combos or len(combo) >= 3 and args.print_triples \
						or len(combo) >= 4 and args.print_quadruples:
					print(str(len(combo)) + "-dice combo! " + str(initialRoll)
						+ " times " + str(multiplier) + " equals " + str(self.currentRoll)
						+ " per dice, for a total of "
						+ ("x" + str(self.currentRoll * len(combo))
							if self.isMultiplierDice else
							str(self.currentRoll * len(combo)))
						+ " " + self.damageType.name + ".")
					#print(combo)
		
		if self.isMultiplierDice:
			for other in rolledDice:
				if not other.isMultiplierDice and other.damageType == self.damageType \
						and not other.notRolled:
					other.currentRoll *= self.currentRoll
	
	def getResult(self, rollResult):
		"""Step three: Add this dice's roll to the total damage dealt."""
		if self.isMultiplierDice or self.notRolled:
			return
		
		if self.failed:
			rollResult.setFailed()
		elif not self.isMultiplierDice:
			rollResult.damage[self.damageType.name] += self.currentRoll
	
	def combosWith(self, other):
		return self.valueMultiplier == other.valueMultiplier \
			and self.damageType == other.damageType \
			and self.values[-1] == other.values[-1] \
			and self.isMultiplierDice == other.isMultiplierDice \
			and (self.isMultiplierDice or self.values[0] == 1 and other.values[0] == 1)
	
	def comboValue(self, diceInvolved):
		if self.isMultiplierDice:
			if diceInvolved == 2:
				return 4
			else:
				#Correct value(s) unknown; this is a guess.
				return 8
		elif self.valueMultiplier == 1:
			#It's unknown if this is correct for 4 dice, but it's correct for 2 and 3.
			return diceInvolved
		else:
			if diceInvolved == 2:
				return 5
			elif diceInvolved == 3:
				return 11 + 2.0/3.0
			else:
				#Correct value(s) unknown; this is a guess.
				return 20
	
	def __repr__(self):
		return "<" + self.__str__() + ">"
	
	def __str__(self):
		result = self.damageType.name
		
		if self.isMultiplierDice:
			if result == "attack":
				result = "attk" #To match the in-game text.
			if self.values[0] > 1 and self.values[-1] == 6:
				result += " x > " + str(self.values[0] - 1)
			else:
				result += " x " \
					+ str(self.values[0] * self.valueMultiplier) + "-" \
					+ str(self.values[-1] * self.valueMultiplier)
		else:
			if self.valueMultiplier == 1:
				if self.values[0] == 1 and self.values[-1] == 6:
					pass
				elif self.values[0] != 1 and self.values[-1] == 6:
					result += " >" + str(self.values[0] - 1)
				else:
					result += " " + str(self.values[0]) + "-" + str(self.values[-1])
			else:
				if self.values[0] == 1 and self.values[-1] == 6:
					result = str(self.valueMultiplier) + "x " + result
				else:
					result += " " \
						+ str(self.values[0] * self.valueMultiplier) + "-" \
						+ str(self.values[-1] * self.valueMultiplier)
		
		return result + " dice"

dice = []

#Build the array of dice.
if args.attack_dice:
	for valueMultiplier in args.attack_dice:
		dice.append(Dice(valueMultiplier = valueMultiplier))
if args.poison_dice:
	for valueMultiplier in args.poison_dice:
		dice.append(Dice(valueMultiplier = valueMultiplier, damageType = DamageType.poison))
if args.health_dice:
	for valueMultiplier in args.health_dice:
		dice.append(Dice(valueMultiplier = valueMultiplier, damageType = DamageType.health))
if args.multiplier_dice:
	for maxValue in args.multiplier_dice:
		dice.append(Dice(maxValue = maxValue, isMultiplierDice = True))
if args.greater_than_dice:
	for minValue in args.greater_than_dice:
		dice.append(Dice(minValue = minValue + 1))
if args.multiplier_greater_than_dice:
	for minValue in args.multiplier_greater_than_dice:
		dice.append(Dice(minValue = minValue + 1, isMultiplierDice = True))

#Validate the array of dice.
if len(dice) > 4:
	print("Too many dice! Only the first four will be used.")
	dice = dice[:4]
elif len(dice) == 0:
	print("No dice!")
	print("Sample usage: \"python " + sys.argv[0] + " -a 1 1 -r 2\" (Simulates two attack dice and rolls both of them once a turn.)")
	print("Run \"python " + sys.argv[0] + " -h\" for help and additional examples.");
	sys.exit(1)
else:
	riskyDice = 0
	for d in dice:
		if d.isRisky():
			riskyDice += 1
	
	if riskyDice == 0:
		print("No risky dice! At least one dice must be able to roll a 1. Health dice and multiplier dice don't count.")
		sys.exit(1)

#Print the test parameters.
print("Using these dice:")
for d in dice:
	print(d)
print()

print("Running " + str(args.turns) + " turns, with "
	+ ("up to " + str(args.rolls) if args.rolls > 0 else "unlimited")
	+ " risky roll" + ("s" if args.rolls != 1 else "")
	+ " per turn, "
	+ ("stopping after " + str(args.threshold) + " damage is rolled"
		if args.threshold > 0 else
		"not stopping based on damage")
	+ ".")
if args.rolls <= 0 and args.threshold <= 0:
	print("I think we all know what's going to happen...")
print()

comboAvailable = False
for i in range(len(dice) - 1):
	for j in range(i + 1, len(dice)):
		if dice[i].combosWith(dice[j]):
			comboAvailable = True
			break
	if comboAvailable:
		break

#End of initialization; time to start testing!

totalResult = RollResult()
successfulTurns = 0
startTime = time.clock()

for turn in range(args.turns):
	turnResult = RollResult()
	
	riskyRollCount = 0
	
	allDiceRolled = True
	
	while allDiceRolled:
		rollResult = RollResult()
		
		#When the end condition is met, only roll the safe dice.
		for d in dice:
			if d.isRisky():
				if (riskyRollCount < args.rolls if args.rolls > 0 else True) \
					and (turnResult.totalDamage() < args.threshold if args.threshold > 0 else True):
					d.roll()
					riskyRollCount += 1
				else:
					d.doNotRoll()
					allDiceRolled = False
			else:
				d.roll()
		
		#Apply the multipliers combos.
		for d in dice:
			d.applyRoll(dice, rollResult)
		
		#Add the regular dice to the result.
		for d in dice:
			d.getResult(rollResult)
		
		turnResult.add(rollResult)
		if rollResult.failed:
			turnResult.setFailed()
			break
	
	if not turnResult.failed:
		successfulTurns += 1
	
	totalResult.add(turnResult)
	
	if args.print_turns:
		print(turnResult)

#For convenience.
totalAttack = totalResult.damage[DamageType.attack.name]
totalPoison = totalResult.damage[DamageType.poison.name]
totalHealth = totalResult.damage[DamageType.health.name]

#For printing poison results.
def printPoison(initialPoison):
	initialPoison = round(initialPoison)
	poison = initialPoison
	poisonResult = 0
	while poison > 0:
		poisonResult += poison
		poison //= 2 #Two slashes forces an integer result.
	print("\t(" + str(initialPoison) + " initial poison damage deals " \
		+ str(poisonResult) + " in all.)")

#Print the results.
if args.print_turns or args.print_combos or args.print_triples or args.print_quadruples:
	print()
print("Results:")

print(str(successfulTurns) + " successful turn" + ("s" if successfulTurns != 1 else "") + ".")

if totalAttack != 0:
	print("Average attack damage: " + str(totalAttack / args.turns))
	print("\tPer successful turn: " + str(totalAttack / successfulTurns))
if totalPoison != 0:
	print("Average (initial) poison damage: " + str(totalPoison / args.turns))
	print("\tPer successful turn: " + str(totalPoison / successfulTurns))
	printPoison(totalPoison / args.turns)
	printPoison(totalPoison / successfulTurns)
	
if totalHealth != 0:
	print("Average health restored: " + str(totalHealth / args.turns))
	print("\tPer successful turn: " + str(totalHealth / successfulTurns))

if comboAvailable:
	print(totalResult.combosToString())

print("\nFinished in {:.2f} seconds.".format(time.clock() - startTime));
