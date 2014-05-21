package com.example.sparkfun_avc;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;

public class SensorDumpThread extends Thread {
    DatagramSocket datagramSocket;
    boolean running;
    final int frequencyMilliseconds;
    LocationManager manager;
    final String bestProvider;
    final InetAddress address;
    final int port;
    final MyLocationListener listener;

    public SensorDumpThread(
            DatagramSocket datagramSocket,
            LocationManager manager,
            String bestProvider,
            final InetAddress address,
            final int port
    ) {
        this(datagramSocket, manager, bestProvider, address, port, 100);
    }

    public SensorDumpThread(
            DatagramSocket datagramSocket,
            LocationManager manager,
            String bestProvider,
            final InetAddress address,
            final int port,
            final int frequencyMilliseconds
    ) {
        super("SensorDumpThread");
        this.datagramSocket = datagramSocket;
        this.manager = manager;
        this.bestProvider = bestProvider;
        this.address = address;
        this.port = port;
        this.frequencyMilliseconds = frequencyMilliseconds;

        this.running = true;

        listener = new MyLocationListener();
        this.manager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                frequencyMilliseconds,
                0,
                listener
        );
    }

    public void stopDumping() {
        this.running = false;
    }

    @Override
    public void run() {
        while (!datagramSocket.isClosed() && running) {
            final Location location = listener.location;

            String json;
            if (location != null) {
                try {
                    final double latitude = location.getLatitude();
                    final double longitude = location.getLongitude();
                    final float bearing = location.getBearing();
                    json = String.format("{" +
                            "\"type\": \"telemetry\"," +
                            "\"latitude\": %4.9f," +
                            "\"longitude\": %4.9f," +
                            "\"bearing\": %4.9f" +
                            "}",
                            latitude,
                            longitude,
                            bearing
                    );
                } catch (Exception e) {
                    json = e.toString();
                }

                byte[] buffer = json.getBytes();
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length, address, port);
                try {
                    datagramSocket.send(packet);
                } catch (IOException e) {
                    // Ignore
                }
            }

            try {
                Thread.sleep(this.frequencyMilliseconds);
            } catch (InterruptedException ie) {
                // Ignore
            }
        }
    };

    protected class MyLocationListener implements LocationListener {
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
        public void onStatusChanged(final String provider, int status, Bundle extras) {
        }
    };
}
