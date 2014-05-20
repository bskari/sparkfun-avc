package com.example.sparkfun_avc;

import java.net.DatagramSocket;

public class SensorDumpThread extends Thread {
	DatagramSocket datagramSocket;
	boolean running;
	int frequencyMilliseconds;
	
	public SensorDumpThread(DatagramSocket datagramSocket) {
		super("SensorDumpThread");
		this.datagramSocket = datagramSocket;
		this.running = true;
		this.frequencyMilliseconds = 100;
	}
	
	public SensorDumpThread(
		DatagramSocket datagramSocket,
		final int frequencyMilliseconds
	) {
		super("SensorDumpThread");
		this.datagramSocket = datagramSocket;
		this.running = true;
		this.frequencyMilliseconds = frequencyMilliseconds;
	}
	
	public void stopDumping() {
		this.running = false;
	}
	
	@Override
	public void run() {
		while (!datagramSocket.isClosed() && running) {
			// Read from the sensors
			// Send the sensor data
			
			try {
				Thread.sleep(this.frequencyMilliseconds);
			} catch (InterruptedException ie) {
				// Ignore
			}
		}
	}

}
