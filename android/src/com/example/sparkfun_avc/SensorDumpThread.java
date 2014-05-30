package com.example.sparkfun_avc;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;

public class SensorDumpThread extends Thread {
	DatagramSocket datagramSocket;
	boolean running;
	final int frequencyMilliseconds;
	final InetAddress address;
	final int port;

	final MyLocationListener locationListener;
	final MySensorEventListener gyroscopeListener;
	final MySensorEventListener linearAccelerationListener;
	final MySensorEventListener magneticFieldListener;

	public SensorDumpThread(final DatagramSocket datagramSocket,
			final LocationManager manager, final InetAddress address,
			final int port, final Context context) {
		this(datagramSocket, manager, address, port, 100, context);
	}

	public SensorDumpThread(final DatagramSocket datagramSocket,
			final LocationManager manager, final InetAddress address,
			final int port, final int frequencyMilliseconds,
			final Context context) {
		super("SensorDumpThread");
		this.datagramSocket = datagramSocket;
		this.address = address;
		this.port = port;
		this.frequencyMilliseconds = frequencyMilliseconds;

		running = true;

		final SensorManager sensorManager = (SensorManager) context
				.getSystemService(Context.SENSOR_SERVICE);

		locationListener = new MyLocationListener();
		manager.requestLocationUpdates(LocationManager.GPS_PROVIDER,
				frequencyMilliseconds, 0, locationListener);

		// TODO: These might come back as null on some devices, so deal with it
		final Sensor gyroscope = sensorManager
				.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
		final Sensor linearAcceleration = sensorManager
				.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION);
		final Sensor magneticField = sensorManager
				.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD);

		final int updateRate = SensorManager.SENSOR_DELAY_NORMAL;
		gyroscopeListener = new MySensorEventListener();
		sensorManager
				.registerListener(gyroscopeListener, gyroscope, updateRate);
		linearAccelerationListener = new MySensorEventListener();
		sensorManager.registerListener(linearAccelerationListener,
				linearAcceleration, updateRate);
		magneticFieldListener = new MySensorEventListener();
		sensorManager.registerListener(magneticFieldListener, magneticField,
				updateRate);
	}

	public void stopDumping() {
		this.running = false;
	}

	@Override
	public void run() {
		while (!datagramSocket.isClosed() && running) {
			final Location location = locationListener.location;

			try {
				JSONObject root = new JSONObject();
				root.put("type", "telemetry");

				// location will be null if we don't have a GPS lock yet
				if (location != null) {
					try {
						final double latitude = location.getLatitude();
						final double longitude = location.getLongitude();
						final float bearing = location.getBearing();
						root.put("latitude", latitude);
						root.put("longitude", longitude);
						root.put("bearing", bearing);
					} catch (Exception e) {
						// Ignore
					}
				}

				putArray(root, "gyroscope", gyroscopeListener.values);
				putArray(root, "linearAcceleration",
						linearAccelerationListener.values);
				putArray(root, "magneticField", magneticFieldListener.values);

				if (root.length() <= 1) {
					continue;
				}

				final byte[] buffer = root.toString().getBytes();
				final DatagramPacket packet = new DatagramPacket(buffer,
						buffer.length, address, port);
				try {
					datagramSocket.send(packet);
				} catch (IOException e) {
					// Ignore
				}
			} catch (JSONException e) {
				e.printStackTrace(System.err);
			}

			try {
				Thread.sleep(this.frequencyMilliseconds);
			} catch (InterruptedException ie) {
				// Ignore
			}
		}
	};

	private void putArray(final JSONObject json, final String name,
			final float[] values) throws JSONException {
		if (values == null || values.length == 0) {
			return;
		}
		if (values.length > 0) {
			JSONArray array = new JSONArray();
			for (float f : values) {
				array.put(f);
			}
			json.put(name, array);
		} else {
			json.put(name, values[0]);
		}
	}

	private class MyLocationListener implements LocationListener {
		public Location location;

		@Override
		public void onLocationChanged(Location location) {
			this.location = location;
		}

		@Override
		public void onProviderEnabled(final String provider) {
		}

		@Override
		public void onProviderDisabled(final String provider) {
		}

		@Override
		public void onStatusChanged(final String provider, final int status,
				final Bundle extras) {
		}
	};

	private class MySensorEventListener implements SensorEventListener {
		public float[] values;

		@Override
		public void onAccuracyChanged(Sensor sensor, int accuracy) {
		}

		@Override
		public void onSensorChanged(SensorEvent event) {
			values = event.values;
		}
	};
}
