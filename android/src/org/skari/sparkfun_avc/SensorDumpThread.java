package org.skari.sparkfun_avc;

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
	final LocationManager locationManager;

	final SensorManager sensorManager;

	final MyLocationListener locationListener;
	final MySensorEventListener gyroscopeListener;
	final MySensorEventListener linearAccelerationListener;
	final MySensorEventListener magneticFieldListener;
	final MySensorEventListener accelerometerListener;

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
		this.locationManager = manager;
		this.address = address;
		this.port = port;
		this.frequencyMilliseconds = frequencyMilliseconds;

		running = true;

		sensorManager = (SensorManager) context
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
		final Sensor accelerometer = sensorManager
				.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);

		final int updateRate = SensorManager.SENSOR_DELAY_NORMAL;
		gyroscopeListener = new MySensorEventListener();
		linearAccelerationListener = new MySensorEventListener();
		magneticFieldListener = new MySensorEventListener();
		accelerometerListener = new MySensorEventListener();
		sensorManager
				.registerListener(gyroscopeListener, gyroscope, updateRate);
		sensorManager.registerListener(linearAccelerationListener,
				linearAcceleration, updateRate);
		sensorManager.registerListener(magneticFieldListener, magneticField,
				updateRate);
		sensorManager.registerListener(accelerometerListener, accelerometer,
				updateRate);
	}

	public void stopDumping() {
		this.running = false;
		sensorManager.unregisterListener(gyroscopeListener);
		sensorManager.unregisterListener(linearAccelerationListener);
		sensorManager.unregisterListener(magneticFieldListener);
		sensorManager.unregisterListener(accelerometerListener);
	}

	@Override
	public void run() {
		while (!datagramSocket.isClosed() && running) {
			final Location location =
					locationManager.getLastKnownLocation("gps");

			try {
				JSONObject root = new JSONObject();
				root.put("type", "telemetry");

				// location will be null if we don't have a GPS lock yet
				if (location != null) {
					try {
						final double latitude = location.getLatitude();
						final double longitude = location.getLongitude();
						final float accuracy = location.getAccuracy();
						final float speed = location.getSpeed();

						root.put("latitude", latitude);
						root.put("longitude", longitude);
						root.put("accuracy", accuracy);
						root.put("speed", speed);
						if (location.hasBearing()) {
							final float bearing = location.getBearing();
							root.put("bearing", bearing);
						}
						try {
							final float heading = getHeading();
							root.put("heading", heading);
						} catch (Exception e) {
							// Ignore
						}
					} catch (Exception e) {
						// Ignore
					}
				}

				putArray(root, "gyroscope", gyroscopeListener.values);
				putArray(root, "linearAcceleration",
						linearAccelerationListener.values);
				putArray(root, "magneticField", magneticFieldListener.values);
				putArray(root, "accelerometer", accelerometerListener.values);

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

	private float getHeading() throws Exception {
		//final float[] mGravity = accelerometerListener.values;
		final float[] mGravity = {0.0f, 0.0f, 9.8f}; // Assume we're always facing down
		final float[] mGeomagnetic = {
				// Subtract biases introduced by the car
				magneticFieldListener.values[0] - 27.625f,
				magneticFieldListener.values[1] - 5.9375f,
				magneticFieldListener.values[2] - -9.125f
		};
		if (mGravity != null && mGeomagnetic != null) {
			float R[] = new float[9];
			float I[] = new float[9];
			boolean success = SensorManager.getRotationMatrix(R, I, mGravity,
					mGeomagnetic);
			if (success) {
				final float orientation[] = new float[3];
				SensorManager.getOrientation(R, orientation);
				final float azimuth = orientation[0]; // Azimuth, pitch, and
														// roll
				final float degrees = -azimuth * 360.0f
						/ (2.0f * (float) Math.PI);
				if (degrees < 0.0f) {
					return degrees + 360.0f;
				}
				return degrees;
			} else {
				throw new Exception("getRotationMatrix failed");
			}
		} else {
			throw new Exception("mGravity or mGeomegnetic is null");
		}
	}

	// I don't even know if this is necessary anymore because I'm using
	// getLastKNownLocation with a provider directly
	private class MyLocationListener implements LocationListener {

		@Override
		public void onLocationChanged(Location location) {
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
