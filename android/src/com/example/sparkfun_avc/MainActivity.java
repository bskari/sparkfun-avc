package com.example.sparkfun_avc;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.Socket;
import java.net.SocketException;
import java.net.UnknownHostException;

import android.app.AlertDialog;
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
	
	SensorDumpThread sensorDumpThread;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        if (savedInstanceState == null) {
            getSupportFragmentManager().beginTransaction()
                    .add(R.id.container, new PlaceholderFragment())
                    .commit();
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
    		DatagramSocket socket;
			try {
				socket = new DatagramSocket();
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
			} finally {
				socket.close();
			}
			
			// TODO: Wait for a response before making this thread
			
    		//sensorDumpThread = new SensorDumpThread(socket);
    	}
    }
    
    public void stopSensorData(View view) {
    	if (sensorDumpThread != null && sensorDumpThread.isAlive()) {
    		sensorDumpThread.stopDumping();
    	}
    }
    
    private void runOrStop(final boolean run) {
    	if (run && (sensorDumpThread == null || !sensorDumpThread.isAlive())) {
			AlertDialog.Builder builder = new AlertDialog.Builder(this);
			builder.setMessage(R.string.not_running);
			AlertDialog dialog = builder.create();
			dialog.show();
			return;
    	}
    	
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
}
