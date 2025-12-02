
const EventEmitter = require('events');
var DEBUG = false;

var minGear = 1;
var maxGear = 10;

class BikeState extends EventEmitter {

	constructor() {
		super();
		console.log(`[BikeState starting]`);

		// init
		this.data = null;
		this.external = null;
		this.mode = 'ERG'; // ERG ou SIM
		this.gear = 1;
		this.targetPower = null; // Will be set from bike data when available
	};

	// Restart the trainer
	restart() {
		this.mode = 'ERG'; // ERG ou SIM
		this.emit('mode', this.mode);
		// update and compute
		this.data = null;
	};

	// Set the bike under the FTMS control
	setControl() {};

	// Current state
	setData(data) {
		this.data = data;
		// Initialize targetPower from bike data on first reception
		if (this.targetPower === null && 'targetPower' in data) {
			this.targetPower = data.targetPower;
			console.log('[BikeState] Initialized targetPower from bike: ' + this.targetPower);
			this.emit('targetPower', this.targetPower);
		}
		// update
		this.compute();
	};

	setGear(gear) {
		this.gear = gear;
		this.emit('gear', this.gear);
	}

	// Gear Up
	GearUp() {
		this.gear++;
		if (this.gear > maxGear)
			this.gear = maxGear;
		this.emit('gear', this.gear);
	};

	// Gear Down
	GearDown() {
		this.gear--;
		if (this.gear < minGear)
			this.gear = minGear;
		this.emit('gear', this.gear);
	};

	/* Puissance a atteindre */
	setTargetPower(power) {
		this.mode = 'ERG'; // ERG
		this.emit('mode', this.mode);
		this.targetPower = power;
		this.emit('targetPower', this.targetPower);
		this.emit('simpower', this.targetPower);
	};

	/* Modifie la puissance target */
	addPower(increment) {
		this.targetPower += increment;
		// Clamp power between 0 and 1000W
		this.targetPower = Math.max(0, Math.min(1000, this.targetPower));
		this.emit('targetPower', this.targetPower);
		this.emit('simpower', this.targetPower);
	};

	/* Mode Simulation : les conditions externes a simuler */
	setExternalCondition(windspeed, grade, crr, cw) {
		this.mode = 'SIM'; // ERG ou SIM
		this.emit('mode', this.mode);
		this.external = {
			windspeed: windspeed,
			grade: grade,
			crr: crr,
			cw: cw
		};
		this.emit('windspeed', (windspeed * 3.6).toFixed(1));
		this.emit('grade', (grade).toFixed(1));
	};

	// Do the math
	compute() {
		// rien si en mode ERG
		if (this.mode === 'ERG')
			return;
		// pas de data du velo : on ne peut rien faire
		if (this.data == null)
			return;
		// pas de data externe : on ne peut rien faire
		if (this.external == null)
			return;

		var simpower = 170 * (1 + 1.15 * (this.data.rpm - 80.0) / 80.0) * (1.0 + 3 * this.external.grade / 100.0);
		// apply gear
		simpower = Math.max(0.0, simpower * (1.0 + 0.1 * (this.gear - 5)));
		// store
		simpower = simpower.toFixed(1);

		if (DEBUG) {
			console.log('[BikeState.js] - SIM rpm: ', this.data.rpm);
			console.log('[BikeState.js] - SIM pente: ', this.external.grade);
			console.log('[BikeState.js] - SIM gear : ', this.gear);
			console.log('[BikeState.js] - SIM calculated power: ', simpower);
		}

		this.emit('simpower', simpower);
	};
};

module.exports = BikeState
