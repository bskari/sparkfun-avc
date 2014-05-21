package com.example.sparkfun_avc;

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
    public final static String EXTRA_MESSAGE = "com.example.myfirstapp.MESSAGE";

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
                    .add(R.id.container, new PlaceholderFragment())
                    .commit();
        }

        locationManager = (LocationManager)getSystemService(LOCATION_SERVICE);
        Criteria criteria = new Criteria();
        criteria.setAccuracy(Criteria.ACCURACY_FINE);
        criteria.setPowerRequirement(Criteria.NO_REQUIREMENT);
        criteria.setAltitudeRequired(false);
        //criteria.setBearingAccuracy(Criteria.ACCURACY_FINE);
        criteria.setBearingRequired(true);
        //criteria.setSpeedAccuracy(Criteria.ACCURACY_FINE);
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
        if (sensorDumpThread.isAlive()) {
            sensorDumpThread.stopDumping();
        }

        try {
            sensorDumpThread.join();
        } catch (InterruptedException e) {
            // TODO: Figure out what to do here
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
            View rootView = inflater.inflate(R.layout.fragment_main, container, false);
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
                AlertDialog.Builder builder = new AlertDialog.Builder(this);
                builder.setMessage(R.string.server_not_found);
                AlertDialog dialog = builder.create();
                dialog.show();
                return;
            }

            byte[] buffer = "{\"requestResponse\": true}".getBytes();
            DatagramPacket packet = new DatagramPacket(buffer, buffer.length, address, 8384);
            try {
                if (socket == null || socket.isClosed()) {
                    socket = new DatagramSocket();
                }
            } catch (SocketException se) {
                AlertDialog.Builder builder = new AlertDialog.Builder(this);
                builder.setMessage(R.string.create_socket_error);
                AlertDialog dialog = builder.create();
                dialog.show();
                return;
            }

            try {
                socket.send(packet);
            } catch (IOException ioe) {
                AlertDialog.Builder builder = new AlertDialog.Builder(this);
                builder.setMessage(R.string.socket_error);
                AlertDialog dialog = builder.create();
                dialog.show();
                return;
            }

            // TODO: Wait for a response before making this thread

            sensorDumpThread = new SensorDumpThread(
                    socket,
                    locationManager,
                    bestProvider,
                    address,
                    8384,
                    100
            );
            sensorDumpThread.start();
        }
    }

    public void stopSensorData(View view) {
        if (sensorDumpThread != null && sensorDumpThread.isAlive()) {
            sensorDumpThread.stopDumping();
        }
    }

    private void runOrStop(final boolean run) {
        if (run && (sensorDumpThread == null || !sensorDumpThread.isAlive())) {
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

        byte[] buffer = String.format(
            "{\"requestResponse\": true," +
                    " \"type\": \"command\"," +
                    " \"command\": \"%s\"}",
            run ? "run" : "stop"
        ).getBytes();

        DatagramPacket packet = new DatagramPacket(buffer, buffer.length, address, 8384);
        DatagramSocket socket;
        try {
            socket = new DatagramSocket();
        } catch (SocketException se) {
            alert(getString(R.string.create_socket_error));
            return;
        }

        try {
            socket.send(packet);
        } catch (IOException ioe) {
            alert(getString(R.string.socket_error));
            return;
        } finally {
            socket.close();
        }
    }

    public void run(View view) {
        runOrStop(true);
    }

    public void stop(View view) {
        runOrStop(false);
    }

    private void alert(final String message) {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setMessage(message);
        AlertDialog dialog = builder.create();
        dialog.show();
        return;
    }
}
