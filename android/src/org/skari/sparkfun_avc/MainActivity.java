package org.skari.sparkfun_avc;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketException;
import java.net.UnknownHostException;

import android.app.AlertDialog;
import android.location.Criteria;
import android.location.LocationManager;
import android.os.Bundle;
import android.support.v4.app.Fragment;
import android.support.v7.app.ActionBarActivity;
import android.view.LayoutInflater;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;

public class MainActivity extends ActionBarActivity {
	public final static String EXTRA_MESSAGE = "org.skari.myfirstapp.MESSAGE";

	private SensorDumpThread sensorDumpThread = null;
	private LocationManager locationManager = null;
	private String bestProvider;
	private DatagramSocket socket;

	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		setContentView(R.layout.activity_main);

		if (savedInstanceState == null) {
			getSupportFragmentManager().beginTransaction()
					.add(R.id.container, new PlaceholderFragment()).commit();
		}

		locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);
		Criteria criteria = new Criteria();
		criteria.setAccuracy(Criteria.ACCURACY_FINE);
		criteria.setPowerRequirement(Criteria.NO_REQUIREMENT);
		criteria.setAltitudeRequired(false);
		// criteria.setBearingAccuracy(Criteria.ACCURACY_FINE); // Requires API
		// level 9
		criteria.setBearingRequired(true);
		// criteria.setSpeedAccuracy(Criteria.ACCURACY_FINE); // Requires API
		// level 9
		criteria.setSpeedRequired(true);
		bestProvider = locationManager.getBestProvider(criteria, true);
	}

	@Override
	public void onPause() {
		super.onPause();
	}

	@Override
	public void onResume() {
		super.onResume();
	}

	@Override
	public void onDestroy() {
		super.onDestroy();
		if (sensorDumpThread != null) {
			if (sensorDumpThread.isAlive()) {
				sensorDumpThread.stopDumping();
			}

			try {
				sensorDumpThread.join();
			} catch (InterruptedException e) {
				// TODO Figure out what to do here
			}
		}
	}

	@Override
	public boolean onCreateOptionsMenu(Menu menu) {
		// Inflate the menu; this adds items to the action bar if it is present.
		getMenuInflater().inflate(R.menu.main, menu);
		return true;
	}

	@Override
	public boolean onOptionsItemSelected(MenuItem item) {
		// Handle action bar item clicks here. The action bar will
		// automatically handle clicks on the Home/Up button, so long
		// as you specify a parent activity in AndroidManifest.xml.
		int id = item.getItemId();
		if (id == R.id.action_settings) {
			return true;
		}
		return super.onOptionsItemSelected(item);
	}

	/**
	 * A placeholder fragment containing a simple view.
	 */
	public static class PlaceholderFragment extends Fragment {

		public PlaceholderFragment() {
		}

		@Override
		public View onCreateView(LayoutInflater inflater, ViewGroup container,
				Bundle savedInstanceState) {
			View rootView = inflater.inflate(R.layout.fragment_main, container,
					false);
			return rootView;
		}
	}

	private InetAddress getAddress() throws UnknownHostException {
		EditText editText = (EditText) findViewById(R.id.edit_server_ip);
		final String server = editText.getText().toString();
		return InetAddress.getByName(server);
	}

	public void sendSensorData(View view) {
		if (sensorDumpThread == null || !sensorDumpThread.isAlive()) {
			InetAddress address;
			try {
				address = getAddress();
			} catch (UnknownHostException uhe) {
				alert(getString(R.string.server_not_found));
				return;
			}

			byte[] buffer = "{\"requestResponse\": true}".getBytes();
			DatagramPacket packet = new DatagramPacket(buffer, buffer.length,
					address, 8384);
			try {
				if (socket == null || socket.isClosed()) {
					socket = new DatagramSocket();
				}
			} catch (SocketException se) {
				alert(getString(R.string.create_socket_error));
				return;
			}

			boolean responseReceived = false;
			final DatagramSocket listenSocket;

			try {
				listenSocket = new DatagramSocket(5001,
						InetAddress.getByName("0.0.0.0"));
			} catch (UnknownHostException e) {
				alert(getString(R.string.create_socket_error));
				return;
			} catch (SocketException e) {
				alert(getString(R.string.create_socket_error));
				return;
			}

			final byte[] receiveBuffer = new byte[1024];
			final DatagramPacket receivePacket = new DatagramPacket(
					receiveBuffer, receiveBuffer.length, address, 8384);
			try {
				listenSocket.setSoTimeout(100);

				// Try to get a response a few times, because we're using UDP
				// which
				// might get randomly dropped
				for (int i = 0; i < 3 && !responseReceived; ++i) {
					try {
						socket.send(packet);
					} catch (IOException ioe) {
						continue;
					}

					try {
						listenSocket.receive(receivePacket);
						responseReceived = true;
					} catch (IOException ioe) {
						// Ignore
					}
				}
			} catch (SocketException se) {
				alert(getString(R.string.create_socket_error));
				return;
			} finally {
				if (listenSocket != null) {
					listenSocket.close();
				}
			}

			if (responseReceived) {
				sensorDumpThread = new SensorDumpThread(socket,
						locationManager, address, 8384, 100, this);
				sensorDumpThread.start();
			} else {
				alert(getString(R.string.server_not_responding));
			}
		}
	}

	public void stopSensorData(View view) {
		if (sensorDumpThread != null && sensorDumpThread.isAlive()) {
			sensorDumpThread.stopDumping();
		}
	}

	private void startOrStop(final boolean start) {
		if (start && (sensorDumpThread == null || !sensorDumpThread.isAlive())) {
			alert(getString(R.string.not_running));
			return;
		}

		InetAddress address;
		try {
			address = getAddress();
		} catch (UnknownHostException uhe) {
			alert(getString(R.string.server_not_found));
			return;
		}

		// Try to get a response a few times, because we're using UDP which
		// might get randomly dropped
		boolean responseReceived = false;

		final DatagramSocket listenSocket;
		try {
			listenSocket = new DatagramSocket(5001,
					InetAddress.getByName("0.0.0.0"));
		} catch (UnknownHostException e) {
			alert(getString(R.string.create_socket_error));
			return;
		} catch (SocketException e) {
			alert(getString(R.string.create_socket_error));
			return;
		}

		try {
			listenSocket.setSoTimeout(100);

			final byte[] buffer = String
					.format("{\"requestResponse\": true,"
							+ " \"type\": \"command\","
							+ " \"command\": \"%s\"}", start ? "start" : "stop")
					.getBytes();
			final DatagramPacket packet = new DatagramPacket(buffer,
					buffer.length, address, 8384);
			final byte[] receiveBuffer = new byte[1024];
			final DatagramPacket receivePacket = new DatagramPacket(
					receiveBuffer, receiveBuffer.length, address, 8384);

			if (socket == null || socket.isClosed()) {
				socket = new DatagramSocket();
			}

			for (int i = 0; i < 3 && !responseReceived; ++i) {
				try {
					socket.send(packet);
				} catch (IOException ioe) {
					alert(getString(R.string.socket_error));
					return;
				}

				try {
					listenSocket.receive(receivePacket);
					responseReceived = true;
				} catch (IOException ioe) {
					// Ignore
				}
			}
		} catch (SocketException se) {
			alert(getString(R.string.create_socket_error));
			return;
		} finally {
			if (listenSocket != null) {
				listenSocket.close();
			}
		}

		if (!responseReceived) {
			alert(getString(R.string.server_not_responding));
		}
	}

	public void run(View view) {
		startOrStop(true);
	}

	public void stop(View view) {
		startOrStop(false);
	}

	private void alert(final String message) {
		AlertDialog.Builder builder = new AlertDialog.Builder(this);
		builder.setMessage(message);
		AlertDialog dialog = builder.create();
		dialog.show();
		return;
	}
}