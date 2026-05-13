"""
Local Monitor Dashboard 1.0

Ringkasan:
- Aplikasi dashboard PySide6 untuk monitoring data kapal secara real-time.
- Menerima data serial dalam format CSV text (UTF-8 compatible).
- Menyediakan tampilan map, indikator, plotting time-series, logging CSV, dan analyze tab.

Format data serial yang dibaca (15 kolom):
1) timestamp
2) latitude
3) longitude
4) speedMps
5) Calc_deg_servo_1
6) Calc_deg_servo_2
7) roll
8) pitch
9) yaw
10) zigzag_yaw
11) rpm_prop_1
12) rpm_prop_2
13) battery_1
14) battery_2
15) mode_auto

Catatan pengolahan:
- Parser memproses data per baris newline dan hanya menerima baris dengan 15 kolom.
- Sebagian nilai diproses lagi untuk kebutuhan visualisasi (mis. koreksi rudder, normalisasi tampilan).
"""

import csv
import io
import sys
from bisect import bisect_left
import folium
import serial
from serial.tools import list_ports
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QComboBox,
    QLabel,
    QGridLayout,
    QGroupBox,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QTabWidget,
    QCheckBox,
    QSlider,
)
import pyqtgraph as pg
from time import time


class MapWebView(QWebEngineView):
    """
    WebView widget untuk menampilkan peta interaktif menggunakan Folium.
    
    Class ini menangani:
    - Pembuatan peta Folium dengan Google Hybrid tile
    - Penambahan marker dan trail untuk tracking posisi kapal
    - Update heading indicator untuk menunjukkan arah heading
    - Clear markers dan trail
    
    Attributes:
        folium_map: Objek Folium Map
        trail_coords: List koordinat untuk trail
        marker_count: Counter untuk jumlah marker
        data: BytesIO buffer untuk menyimpan HTML peta
    """
    def __init__(self, initial_coordinates: tuple[float, float]):
        """
        Inisialisasi MapWebView dengan koordinat awal.
        
        Args:
            initial_coordinates: Tuple (latitude, longitude) untuk posisi awal peta
        """
        super().__init__()
        self.folium_map = folium.Map(
            location=initial_coordinates,
            zoom_start=18,
            zoom_control=True,
            attribution_control=True,
            tiles=None  # no default OSM; we'll add Google Hybrid as default
        )
        
        print(f"[MAP] Zoom Level: 18 | Coverage: ~200-500 m | Details: High Detail")
        print(f"[MAP] Max Zoom: 21 | Leaflet.js native support")
        
        # Add satellite tile layers
        self.add_tile_layers()
        
        # Track coordinates for trail
        self.trail_coords = [initial_coordinates]
        self.marker_count = 0
        
        self.data = io.BytesIO()
        self.folium_map.save(self.data, close_file=False)
        self.setHtml(self.data.getvalue().decode())
        
        # Add initial marker after HTML is loaded
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self.add_initial_marker(initial_coordinates))
    
    def add_tile_layers(self):
        """
        Menambahkan tile layers ke peta.
        
        Saat ini hanya menggunakan Google Hybrid (satelit + label) sebagai base layer.
        Tile layers lain (Google Satellite, Bing Satellite, dll) di-comment out.
        """
        # # Google Satellite
        # folium.TileLayer(
        #     tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        #     attr='Google',
        #     name='🌍 Google Satellite',
        #     overlay=False,
        #     control=True,
        #     max_zoom=21,
        #     maxNativeZoom=21
        # ).add_to(self.folium_map)
        
        # # Bing Satellite (High Resolution)
        # folium.TileLayer(
        #     tiles='http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        #     attr='Bing',
        #     name='🛰️ Bing Satellite',
        #     overlay=False,
        #     control=True,
        #     max_zoom=20,
        #     maxNativeZoom=20
        # ).add_to(self.folium_map)
        
        # # CartoDB Dark Matter
        # folium.TileLayer(
        #     tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        #     attr='CartoDB',
        #     name='🌙 Dark Mode',
        #     overlay=False,
        #     control=True,
        #     max_zoom=19,
        #     maxNativeZoom=19
        # ).add_to(self.folium_map)
        
        # # Esri Satellite
        # folium.TileLayer(
        #     tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        #     attr='Esri',
        #     name='🛰️ Esri Satellite',
        #     overlay=False,
        #     control=True,
        #     max_zoom=20,
        #     maxNativeZoom=20
        # ).add_to(self.folium_map)
        
        # Google Hybrid (Satellite + Labels) - Default and only visible base layer
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='Google',
            name='🗺️ Google Hybrid',
            overlay=False,
            control=True,
            max_zoom=21,
            maxNativeZoom=21
        ).add_to(self.folium_map)
        
        # Add layer control
        folium.LayerControl(position='topright').add_to(self.folium_map)
        
        # quiet: removed verbose print
    
    def add_initial_marker(self, coords: tuple[float, float], heading: float | None = None):
        """Add initial marker using JavaScript"""
        self.marker_count += 1
        map_name = self.folium_map.get_name()
        
        # Build popup content
        if heading is not None:
            popup_content = f'🚢 Start Position\\nLat: {coords[0]:.6f}\\nLon: {coords[1]:.6f}\\nHeading: {heading:.1f}°'
        else:
            popup_content = f'🚢 Start Position\\nLat: {coords[0]:.6f}\\nLon: {coords[1]:.6f}'
        
        js_code = f"""
        // Add initial marker
        var startMarker = L.marker({list(coords)})
            .addTo({map_name})
            .bindPopup('{popup_content}')
            .bindTooltip('Start Point');
        window.startMarker = startMarker;
        
        // Create marker group for trail markers
        window.trailMarkers = L.layerGroup().addTo({map_name});
        
        // Create polyline for trail (menghubungkan semua points)
        window.trailLine = L.polyline([{list(coords)}], {{
            color: '#3b82f6',
            weight: 3,
            opacity: 0.8,
            lineCap: 'round',
            lineJoin: 'round'
        }}).addTo({map_name});
        window.trailLine.bringToFront();
        
        console.log('✅ Initial marker and trail line created');
        """
        
        self.page().runJavaScript(js_code)
        # quiet
    
    def add_marker_js(self, coords: tuple[float, float], heading: float | None = None):
        """Add marker using JavaScript without regenerating HTML"""
        self.marker_count += 1
        self.trail_coords.append(coords)
        
        map_name = self.folium_map.get_name()
        
        # Build popup content
        if heading is not None:
            popup_content = f'📍 Point {self.marker_count}\\nLat: {coords[0]:.6f}\\nLon: {coords[1]:.6f}\\nHeading: {heading:.1f}°'
        else:
            popup_content = f'📍 Point {self.marker_count}\\nLat: {coords[0]:.6f}\\nLon: {coords[1]:.6f}'
        
        js_code = f"""
        // Add new marker
        var newMarker = L.marker({list(coords)})
            .bindPopup('{popup_content}')
            .bindTooltip('Point {self.marker_count}');
        
        // Add to marker group
        window.trailMarkers.addLayer(newMarker);
        
        // Update trail line with all coordinates
        if (window.trailLine) {{
            var allCoords = {[list(coord) for coord in self.trail_coords]};
            window.trailLine.setLatLngs(allCoords);
            window.trailLine.bringToFront();  // Pastikan visible di depan
        }}
        
        console.log('✅ Marker {self.marker_count} added at {list(coords)} | Trail points: {len(self.trail_coords)}');
        """
        
        self.page().runJavaScript(js_code)
        # quiet

    def update_heading_line(self, origin: tuple[float, float], heading_deg: float, length_m: float = 5.0):
        """
        Create atau update garis heading dari posisi saat ini.
        
        Args:
            origin: Tuple (latitude, longitude) untuk posisi awal
            heading_deg: Heading dalam derajat (0-360°)
            length_m: Panjang garis heading dalam meter (default: 20.0 m)
            
        Method ini:
        - Menghitung koordinat tujuan berdasarkan heading dan panjang
        - Membuat atau update polyline untuk heading indicator
        - Menggunakan warna merah untuk heading line
        """
        import math
        lat1 = math.radians(origin[0])
        lon1 = math.radians(origin[1])
        brng = math.radians(heading_deg % 360.0)
        R = 6371000.0
        dR = length_m / R
        lat2 = math.asin(math.sin(lat1) * math.cos(dR) + math.cos(lat1) * math.sin(dR) * math.cos(brng))
        lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(dR) * math.cos(lat1), math.cos(dR) - math.sin(lat1) * math.sin(lat2))
        dest = (math.degrees(lat2), math.degrees(lon2))

        map_name = self.folium_map.get_name()
        js_code = f"""
        (function() {{
          var pts = [{list(origin)}, {list(dest)}];
          if (!window.headingLine) {{
            window.headingLine = L.polyline(pts, {{ color: 'red', weight: 4, opacity: 0.9 }}).addTo({map_name});
          }} else {{
            window.headingLine.setLatLngs(pts);
          }}
        }})();
        """
        self.page().runJavaScript(js_code)

    def add_heading_line_segment(self, origin: tuple[float, float], heading_deg: float, length_m: float = 5.0):
        """
        Add heading line segment (used for Analyze tab to draw multiple headings).

        Args:
            origin: Tuple (lat, lon)
            heading_deg: heading in degrees
            length_m: length of line
        """
        import math
        lat1 = math.radians(origin[0])
        lon1 = math.radians(origin[1])
        brng = math.radians(heading_deg % 360.0)
        R = 6371000.0
        dR = length_m / R
        lat2 = math.asin(math.sin(lat1) * math.cos(dR) + math.cos(lat1) * math.sin(dR) * math.cos(brng))
        lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(dR) * math.cos(lat1), math.cos(dR) - math.sin(lat1) * math.sin(lat2))
        dest = (math.degrees(lat2), math.degrees(lon2))

        map_name = self.folium_map.get_name()
        js_code = f"""
        (function() {{
          var mapRef = {map_name};
          if (!window.headingLinesGroup) {{
            window.headingLinesGroup = L.layerGroup().addTo(mapRef);
            window.headingLineLayers = [];
          }}
          var pts = [{list(origin)}, {list(dest)}];
          var seg = L.polyline(pts, {{ color: 'red', weight: 3, opacity: 0.9 }}).addTo(window.headingLinesGroup);
          window.headingLineLayers.push(seg);
        }})();
        """
        self.page().runJavaScript(js_code)
    
    def move_start_marker(self, coords: tuple[float, float], heading: float | None = None, timestamp: float | None = None):
        """
        Pindahkan marker awal (start marker) ke koordinat baru dan update popup/tooltip.
        """
        map_name = self.folium_map.get_name()
        popup_lines = [
            f"t = {timestamp:.3f} s" if timestamp is not None else None,
            f"Lat: {coords[0]:.6f}",
            f"Lon: {coords[1]:.6f}",
            f"Heading: {heading:.1f}°" if heading is not None else None
        ]
        popup_content = "\\n".join([line for line in popup_lines if line])
        tooltip_content = popup_content.replace("\\n", ", ")
        popup_js = popup_content.replace("\\", "\\\\").replace("'", "\\'")
        tooltip_js = tooltip_content.replace("\\", "\\\\").replace("'", "\\'")
        js_code = f"""
        (function() {{
          var coords = {list(coords)};
          var popupContent = '{popup_js}';
          var tooltipContent = '{tooltip_js}';
          if (window.startMarker) {{
            window.startMarker.setLatLng(coords);
            var popup = window.startMarker.getPopup();
            if (popup) {{
              popup.setContent(popupContent);
            }} else {{
              window.startMarker.bindPopup(popupContent);
            }}
            window.startMarker.unbindTooltip();
            window.startMarker.bindTooltip(tooltipContent, {{
              direction: 'top',
              opacity: 0.95,
              sticky: true,
              className: 'active-marker-tooltip',
              offset: [0, -30]
            }});
          }} else {{
            window.startMarker = L.marker(coords)
              .addTo({map_name})
              .bindPopup(popupContent)
              .bindTooltip(tooltipContent, {{
                direction: 'top',
                opacity: 0.95,
                sticky: true,
                className: 'active-marker-tooltip',
                offset: [0, -30]
              }});
          }}
          if (window.startMarker && window.startMarker.setOpacity) {{
            window.startMarker.setOpacity(1);
          }}
          if (window.startMarker && window.startMarker.openTooltip) {{
            window.startMarker.openTooltip();
          }}
        }})();
        """
        self.page().runJavaScript(js_code)

    def update_slider_heading_line(self, origin: tuple[float, float] | None, heading_deg: float | None, length_m: float = 5.0):
        """
        Update garis heading khusus pointer slider Analyze.
        """
        map_name = self.folium_map.get_name()
        if origin is None or heading_deg is None:
            js_code = f"""
            (function() {{
              if (window.sliderHeadingLine) {{
                {map_name}.removeLayer(window.sliderHeadingLine);
                window.sliderHeadingLine = null;
              }}
            }})();
            """
            self.page().runJavaScript(js_code)
            return

        import math
        lat1 = math.radians(origin[0])
        lon1 = math.radians(origin[1])
        brng = math.radians(heading_deg % 360.0)
        R = 6371000.0
        dR = length_m / R
        lat2 = math.asin(math.sin(lat1) * math.cos(dR) + math.cos(lat1) * math.sin(dR) * math.cos(brng))
        lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(dR) * math.cos(lat1), math.cos(dR) - math.sin(lat1) * math.sin(lat2))
        dest = (math.degrees(lat2), math.degrees(lon2))

        js_code = f"""
        (function() {{
          var pts = [{list(origin)}, {list(dest)}];
          if (window.sliderHeadingLine) {{
            window.sliderHeadingLine.setLatLngs(pts);
          }} else {{
            window.sliderHeadingLine = L.polyline(pts, {{
              color: 'red',
              weight: 4,
              opacity: 0.95,
              dashArray: '6, 6'
            }}).addTo({map_name});
          }}
          window.sliderHeadingLine.bringToFront();
        }})();
        """
        self.page().runJavaScript(js_code)

    def update_map(self, new_coords: tuple[float, float], heading_deg: float | None = None):
        """
        Update peta dengan koordinat baru dan heading.
        
        Args:
            new_coords: Tuple (latitude, longitude) untuk posisi baru
            heading_deg: Heading dalam derajat (optional, default: None)
            
        Method ini:
        - Update posisi peta ke koordinat baru
        - Menambahkan marker untuk posisi baru
        - Update heading indicator jika heading disediakan
        - Memindahkan view peta ke posisi baru
        """
        # Update Python object location
        self.folium_map.location = new_coords
        
        # Add marker for new position (with heading if available)
        self.add_marker_js(new_coords, heading_deg)
        
        # Update heading line if provided
        if heading_deg is not None:
            try:
                self.update_heading_line(new_coords, float(heading_deg))
            except Exception:
                pass
        
        # Move map view to new position
        map_name = self.folium_map.get_name()
        js_code = f'{map_name}.setView({list(new_coords)})'
        self.page().runJavaScript(js_code)
        
        # quiet

    def clear_markers(self):
        """
        Clear semua marker dan trail dari peta.
        
        Method ini:
        - Clear semua trail markers
        - Clear trail line
        - Clear heading line
        - Reset marker counter
        - Menyimpan koordinat awal (jika ada)
        """
        # Reset Python data
        self.trail_coords = [self.trail_coords[0]] if self.trail_coords else []  # Keep initial coord
        self.marker_count = 0
        
        # Clear markers via JavaScript
        map_name = self.folium_map.get_name()
        js_code = f"""
        (function() {{
          // Clear all trail markers
          if (window.trailMarkers) {{
            window.trailMarkers.clearLayers();
          }}
          
          // Clear trail line
          if (window.trailLine) {{
            {map_name}.removeLayer(window.trailLine);
          }}
          
          // Clear heading line
          if (window.headingLine) {{
            {map_name}.removeLayer(window.headingLine);
          }}

          // Clear multiple heading lines (Analyze tab)
          if (window.headingLinesGroup) {{
            window.headingLinesGroup.clearLayers();
            {map_name}.removeLayer(window.headingLinesGroup);
            window.headingLinesGroup = null;
          }}
          window.headingLineLayers = [];
          
          if (window.sliderHeadingLine) {{
            {map_name}.removeLayer(window.sliderHeadingLine);
            window.sliderHeadingLine = null;
          }}

          if (window.startMarker) {{
            {map_name}.removeLayer(window.startMarker);
            window.startMarker = null;
          }}
          
          console.log('✅ All map markers cleared');
        }})();
        """
        self.page().runJavaScript(js_code)
        print("[MAP] All markers and trails cleared")


class MainWindow(QMainWindow):
    """
    Main window aplikasi dashboard monitoring kapal model.
    
    Class ini menangani:
    - Serial communication dengan ESP32-S3 receiver
    - Menampilkan peta interaktif dengan posisi kapal
    - Menampilkan time series plots untuk berbagai parameter
    - Menampilkan live indicators untuk nilai real-time
    - CSV logging untuk menyimpan data
    
    Attributes:
        ser: Objek Serial untuk komunikasi serial
        serial_timer: QTimer untuk polling serial data
        log_file: File object untuk logging CSV
        map_webview: Objek MapWebView untuk menampilkan peta
        rpm_plot_widget: PyQtGraph widget untuk plot RPM
        attitude_plot_widget: PyQtGraph widget untuk plot Roll/Pitch
        yaw_plot_widget: PyQtGraph widget untuk plot Yaw/Zigzag Yaw
        rudder_plot_widget: PyQtGraph widget untuk plot Rudder
    """
    def __init__(self):
        """
        Inisialisasi MainWindow dengan semua komponen GUI.
        
        Membuat:
        - Control panel (port, baud rate, map marker rate)
        - Indicator panel (live values)
        - Map webview
        - Time series plots (RPM, Roll/Pitch, Yaw, Rudder)
        - Serial communication setup
        - Logging setup
        """
        super().__init__()
        self.resize(800, 700)
        self.setWindowTitle("Ship Model Local Dashboard")
        self.tab_widget = QTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        
        # Tab "Live Data" menampung seluruh layout eksisting
        live_tab = QWidget(self)
        live_tab.setLayout(QHBoxLayout())
        live_tab.layout().setContentsMargins(0, 0, 0, 0)
        
        # Starting position (Surabaya)
        self.base_lat = -7.281500
        self.base_lon = 112.798900
        
        # Rudder correction offsets (deg)
        self.correction_deg_servo_1 = -1.643
        self.correction_deg_servo_2 = -1.436
        
        # Serial state
        self.ser = None
        self.serial_timer = QTimer(self)
        self.serial_timer.timeout.connect(self.poll_serial)
        
        # Plot interval control (decimation)
        self.plot_counter = 0
        self.plot_interval = 10  # Default: plot setiap 10 data
        
        # Logging state
        self.log_btn = None
        self.log_file_path = None
        self.log_file = None
        self.log_buffer = []
        self.log_timer = QTimer(self)
        self.log_timer.setInterval(400)  # flush every 400 ms
        self.log_timer.timeout.connect(self.flush_log_buffer)
        
        # Helper connection state method
        def _is_connected() -> bool:
            return bool(self.ser and getattr(self.ser, 'is_open', False) and self.serial_timer.isActive())
        self.is_connected = _is_connected
        
        # Right side wrapper panel (1/4 width)
        right_panel = QWidget(self)
        right_panel.setLayout(QVBoxLayout())
        right_panel.layout().setContentsMargins(0, 0, 0, 0)

        # Controls panel (top of right panel)
        controls_panel = QGroupBox("", self)
        controls_panel.setLayout(QVBoxLayout())
        controls_panel.layout().setContentsMargins(12, 12, 12, 12)

        # Grid 2x3: (row,col) =>
        # (0,0) Port label, (0,1) Port dropdown, (0,2) Refresh button
        # (1,0) Baud label, (1,1) Baud dropdown, (1,2) empty
        grid_widget = QWidget(self)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        port_label = QLabel("Port:")
        self.port_combo = QComboBox(self)
        self.refresh_ports()
        self.refresh_btn = QPushButton("Refresh Ports", self)
        self.refresh_btn.clicked.connect(self.refresh_ports)

        baud_label = QLabel("Baud:")
        self.baud_combo = QComboBox(self)
        self.baud_combo.addItems(["115200", "57600", "38400", "19200", "9600", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")

        map_marker_label = QLabel("Map Marker:")
        self.plot_int_combo = QComboBox(self)
        # Combo box items: marker per detik (@ 10Hz sampling)
        # Format: "value" -> interval calculation: 10/value
        self.plot_int_combo.addItems(["10", "5", "2", "1", "0.5", "0.2", "0.1"])
        self.plot_int_combo.setCurrentText("1")  # Default: 1 marker/detik
        self.plot_int_combo.setToolTip("Jumlah marker yang di-plot ke map per detik (@ 10Hz sampling)")
        map_marker_unit_label = QLabel("per detik")

        grid.addWidget(port_label, 0, 0)
        grid.addWidget(self.port_combo, 0, 1)
        grid.addWidget(self.refresh_btn, 0, 2)
        grid.addWidget(baud_label, 1, 0)
        grid.addWidget(self.baud_combo, 1, 1)
        # (1,2) intentionally left empty
        grid.addWidget(map_marker_label, 2, 0)
        grid.addWidget(self.plot_int_combo, 2, 1)
        grid.addWidget(map_marker_unit_label, 2, 2)

        grid_widget.setLayout(grid)
        controls_panel.layout().addWidget(grid_widget)

        row3 = QWidget(self)
        row3.setLayout(QHBoxLayout())
        row3.layout().setContentsMargins(0, 0, 0, 0)
        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(self.toggle_connection)
        row3.layout().addWidget(self.connect_btn)
        # Start/Stop Log toggle
        self.log_btn = QPushButton("Start Log", self)
        self.log_btn.setCheckable(True)
        self.log_btn.clicked.connect(self.toggle_logging)
        row3.layout().addWidget(self.log_btn)
        controls_panel.layout().addWidget(row3)

        # Initial UI states
        self.log_btn.setEnabled(False)

        controls_panel.layout().addStretch(1)

        # Reserved panel for future UI elements (bottom of right panel)
        indicator_panel = QGroupBox("", self)
        indicator_panel.setLayout(QVBoxLayout())
        indicator_panel.layout().setContentsMargins(12, 12, 12, 12)
        # indicator indicators grid
        indicator = QWidget(self)
        indicator.setLayout(QGridLayout())
        indicator.layout().setContentsMargins(0, 0, 0, 0)
        indicator.layout().setHorizontalSpacing(10)
        indicator.layout().setVerticalSpacing(8)

        # Dials: Roll, Pitch, Yaw
        self.roll_label = QLabel("0.0°", self)
        self.roll_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        self.pitch_label = QLabel("0.0°", self)
        self.pitch_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        self.yaw_label = QLabel("0.0°", self)
        self.yaw_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        self.zigzag_yaw_label = QLabel("0.0°", self)
        self.zigzag_yaw_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        
        # Row 0: Roll & Pitch labels
        indicator.layout().addWidget(QLabel("Roll (°)"), 0, 0)
        indicator.layout().addWidget(QLabel("Pitch (°)"), 0, 1)
        # Row 1: Roll & Pitch values
        indicator.layout().addWidget(self.roll_label, 1, 0)
        indicator.layout().addWidget(self.pitch_label, 1, 1)

        # Row 2: Yaw & Zigzag Yaw labels
        indicator.layout().addWidget(QLabel("Yaw (°)"), 2, 0)
        indicator.layout().addWidget(QLabel("Zigzag Yaw (°)"), 2, 1)
        # Row 3: Yaw & Zigzag Yaw values
        indicator.layout().addWidget(self.yaw_label, 3, 0)
        indicator.layout().addWidget(self.zigzag_yaw_label, 3, 1)

        # Labels: Rudder 1/2 (small range -45..45)
        self.rud1_label = QLabel("0.0°", self)
        self.rud1_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        self.rud2_label = QLabel("0.0°", self)
        self.rud2_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        
        # Row 4: Rudder 1 & Rudder 2 labels
        indicator.layout().addWidget(QLabel("Rudder 1 (°)"), 4, 0)
        indicator.layout().addWidget(QLabel("Rudder 2 (°)"), 4, 1)
        # Row 5: Rudder 1 & Rudder 2 values
        indicator.layout().addWidget(self.rud1_label, 5, 0)
        indicator.layout().addWidget(self.rud2_label, 5, 1)

        # Numeric indicator labels
        self.speed_label = QLabel("0.00 m/s", self)
        self.speed_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        self.mode_label = QLabel("Manual", self)
        self.mode_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13pt; text-align: center;")
        
        # Row 6: GPS Speed & Mode labels
        indicator.layout().addWidget(QLabel("GPS Speed (m/s)"), 6, 0)
        indicator.layout().addWidget(QLabel("Mode"), 6, 1)
        # Row 7: GPS Speed & Mode values
        indicator.layout().addWidget(self.speed_label, 7, 0)
        indicator.layout().addWidget(self.mode_label, 7, 1)

        # Row 8: RPM Propeller 1 & 2 labels
        self.rpm1_label = QLabel("0 RPM", self)
        self.rpm1_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        self.rpm2_label = QLabel("0 RPM", self)
        self.rpm2_label.setStyleSheet("color: #e5e7eb; font-weight: bold; font-size: 13pt; text-align: center;")
        
        indicator.layout().addWidget(QLabel("RPM Propeller 1"), 8, 0)
        indicator.layout().addWidget(QLabel("RPM Propeller 2"), 8, 1)
        # Row 9: RPM Propeller 1 & 2 values
        indicator.layout().addWidget(self.rpm1_label, 9, 0)
        indicator.layout().addWidget(self.rpm2_label, 9, 1)

        # Row 10: Battery Control & Motor Propeller labels
        self.bat1_label = QLabel("12.00 V", self)
        self.bat1_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13pt; text-align: center;")
        self.bat2_label = QLabel("12.00 V", self)
        self.bat2_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13pt; text-align: center;")
        
        indicator.layout().addWidget(QLabel("Battery Control"), 10, 0)
        indicator.layout().addWidget(QLabel("Battery Motor"), 10, 1)
        # Row 11: Battery Control & Motor Propeller values
        indicator.layout().addWidget(self.bat1_label, 11, 0)
        indicator.layout().addWidget(self.bat2_label, 11, 1)

        indicator_panel.layout().addWidget(indicator)
        indicator_panel.layout().addStretch(1)

        # Left: Map panel divided into left_panel_A and left_panel_B (horizontal split)
        left_panel = QWidget(self)
        left_panel.setLayout(QHBoxLayout())
        left_panel.layout().setContentsMargins(0, 0, 0, 0)
        
        # Left Panel A (left side) - divided into top and bottom (vertical split)
        left_panel_A = QWidget(self)
        left_panel_A.setLayout(QVBoxLayout())
        left_panel_A.layout().setContentsMargins(0, 0, 0, 0)
        
        # Left Panel A - Top: Map WebView
        left_panel_A_top = QWidget(self)
        left_panel_A_top.setLayout(QVBoxLayout())
        left_panel_A_top.layout().setContentsMargins(0, 0, 0, 0)
        self.map_webview = MapWebView((self.base_lat, self.base_lon))
        left_panel_A_top.layout().addWidget(self.map_webview)
        
        # Left Panel A - Bottom
        left_panel_A_bottom = QWidget(self)
        left_panel_A_bottom.setLayout(QVBoxLayout())
        left_panel_A_bottom.layout().setContentsMargins(0, 0, 0, 0)
        
        # Create RPM Time Series Plot using pyqtgraph
        self.rpm_plot_widget = pg.PlotWidget()
        self.rpm_plot_widget.setLabel('left', 'RPM', color='#e5e7eb', **{'font-size': '12pt'})
        self.rpm_plot_widget.setLabel('bottom', 'Time (s)', color='#e5e7eb', **{'font-size': '12pt'})
        self.rpm_plot_widget.setTitle('RPM Propeller Time Series', color='#e5e7eb', size='12pt')
        self.rpm_plot_widget.setBackground('#1f2937')
        self.rpm_plot_widget.addLegend(offset=(10, 10))
        
        # Set grid and style
        self.rpm_plot_widget.showGrid(x=False, y=False)
        self.rpm_plot_widget.getAxis('left').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.rpm_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.rpm_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.rpm_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#e5e7eb'))
        
        # Create data storage for time series
        self.rpm_time_data = []  # x axis (time)
        self.rpm1_data = []      # y axis (RPM1)
        self.rpm2_data = []      # y axis (RPM2)
        self.start_time = time()
        self.max_points =  50   # Keep last 50 points atau 5 detik data yang terakhir
        
        # Create line plots for RPM1 and RPM2
        self.rpm1_curve = self.rpm_plot_widget.plot(name='RPM Propeller 1', pen=pg.mkPen(color='#3b82f6', width=2))
        self.rpm2_curve = self.rpm_plot_widget.plot(name='RPM Propeller 2', pen=pg.mkPen(color='#ef4444', width=2))
        
        left_panel_A_bottom.layout().addWidget(self.rpm_plot_widget)
        
        # Add A_top and A_bottom to left_panel_A with equal height
        left_panel_A.layout().addWidget(left_panel_A_top, 2)
        left_panel_A.layout().addWidget(left_panel_A_bottom, 1)
        
        # Left Panel B (right side) - divided into top, middle, and bottom (vertical split)
        left_panel_B = QWidget(self)
        left_panel_B.setLayout(QVBoxLayout())
        left_panel_B.layout().setContentsMargins(0, 0, 0, 0)
        
        # Left Panel B - Top: Roll and Pitch Time Series
        left_panel_B_top = QWidget(self)
        left_panel_B_top.setLayout(QVBoxLayout())
        left_panel_B_top.layout().setContentsMargins(0, 0, 0, 0)
        
        self.attitude_plot_widget = pg.PlotWidget()
        self.attitude_plot_widget.setLabel('left', 'Angle (°)', color='#e5e7eb', **{'font-size': '11pt'})
        self.attitude_plot_widget.setLabel('bottom', 'Time (s)', color='#e5e7eb', **{'font-size': '11pt'})
        self.attitude_plot_widget.setTitle('Roll & Pitch Time Series', color='#e5e7eb', size='11pt')
        self.attitude_plot_widget.setBackground('#1f2937')
        self.attitude_plot_widget.addLegend(offset=(10, 10))
        self.attitude_plot_widget.showGrid(x=False, y=False)
        self.attitude_plot_widget.getAxis('left').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.attitude_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.attitude_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.attitude_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#e5e7eb'))
        
        self.attitude_time_data = []
        self.roll_data = []
        self.pitch_data = []
        self.roll_curve = self.attitude_plot_widget.plot(name='Roll', pen=pg.mkPen(color='#f59e0b', width=2))
        self.pitch_curve = self.attitude_plot_widget.plot(name='Pitch', pen=pg.mkPen(color='#8b5cf6', width=2))
        
        left_panel_B_top.layout().addWidget(self.attitude_plot_widget)
        
        # Left Panel B - Middle: Yaw and Zigzag Yaw Time Series
        left_panel_B_middle = QWidget(self)
        left_panel_B_middle.setLayout(QVBoxLayout())
        left_panel_B_middle.layout().setContentsMargins(0, 0, 0, 0)
        
        self.yaw_plot_widget = pg.PlotWidget()
        self.yaw_plot_widget.setLabel('left', 'Yaw (°)', color='#10b981', **{'font-size': '11pt'})
        self.yaw_plot_widget.setLabel('bottom', 'Time (s)', color='#e5e7eb', **{'font-size': '11pt'})
        self.yaw_plot_widget.setTitle('Yaw & Zigzag Yaw Time Series', color='#e5e7eb', size='11pt')
        self.yaw_plot_widget.setBackground('#1f2937')
        self.yaw_plot_widget.addLegend(offset=(10, 10))
        self.yaw_plot_widget.showGrid(x=False, y=False)
        self.yaw_plot_widget.getAxis('left').setPen(pg.mkPen(color='#10b981', width=2))
        self.yaw_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.yaw_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.yaw_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#e5e7eb'))
        
        # Create secondary ViewBox for zigzag yaw (right axis)
        self.yaw_plot_widget_viewbox2 = pg.ViewBox()
        self.yaw_plot_widget.scene().addItem(self.yaw_plot_widget_viewbox2)
        self.yaw_plot_widget.getAxis('right').linkToView(self.yaw_plot_widget_viewbox2)
        self.yaw_plot_widget_viewbox2.setXLink(self.yaw_plot_widget)
        self.yaw_plot_widget.showAxis('right')
        self.yaw_plot_widget.getAxis('right').setLabel('Zigzag Yaw (°)', color='#06b6d4', **{'font-size': '11pt'})
        self.yaw_plot_widget.getAxis('right').setPen(pg.mkPen(color='#06b6d4', width=2))
        self.yaw_plot_widget.getAxis('right').setTextPen(pg.mkPen(color='#e5e7eb'))
        
        # Update view boxes when the plot is resized
        def update_yaw_views():
            self.yaw_plot_widget_viewbox2.setGeometry(self.yaw_plot_widget.getViewBox().sceneBoundingRect())
            self.yaw_plot_widget_viewbox2.linkedViewChanged(self.yaw_plot_widget.getViewBox(), self.yaw_plot_widget_viewbox2.XAxis)
        
        update_yaw_views()
        self.yaw_plot_widget.getViewBox().sigResized.connect(update_yaw_views)
        
        self.yaw_time_data = []
        self.yaw_data = []
        self.zigzag_yaw_data = []
        self.yaw_curve = self.yaw_plot_widget.plot(name='Yaw', pen=pg.mkPen(color='#10b981', width=2))
        self.zigzag_yaw_curve = pg.PlotDataItem(name='Zigzag Yaw', pen=pg.mkPen(color='#06b6d4', width=2))
        self.yaw_plot_widget_viewbox2.addItem(self.zigzag_yaw_curve)
        
        left_panel_B_middle.layout().addWidget(self.yaw_plot_widget)
        
        # Left Panel B - Bottom: Rudder 1 and Rudder 2 Time Series
        left_panel_B_bottom = QWidget(self)
        left_panel_B_bottom.setLayout(QVBoxLayout())
        left_panel_B_bottom.layout().setContentsMargins(0, 0, 0, 0)
        
        self.rudder_plot_widget = pg.PlotWidget()
        self.rudder_plot_widget.setLabel('left', 'Angle (°)', color='#e5e7eb', **{'font-size': '11pt'})
        self.rudder_plot_widget.setLabel('bottom', 'Time (s)', color='#e5e7eb', **{'font-size': '11pt'})
        self.rudder_plot_widget.setTitle('Rudder 1 & 2 Time Series', color='#e5e7eb', size='11pt')
        self.rudder_plot_widget.setBackground('#1f2937')
        self.rudder_plot_widget.addLegend(offset=(10, 10))
        self.rudder_plot_widget.showGrid(x=False, y=False)
        self.rudder_plot_widget.getAxis('left').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.rudder_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.rudder_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.rudder_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#e5e7eb'))
        
        self.rudder_time_data = []
        self.rud1_data = []
        self.rud2_data = []
        self.rud1_curve = self.rudder_plot_widget.plot(name='Rudder 1', pen=pg.mkPen(color='#ec4899', width=2))
        self.rud2_curve = self.rudder_plot_widget.plot(name='Rudder 2', pen=pg.mkPen(color='#14b8a6', width=2))
        
        left_panel_B_bottom.layout().addWidget(self.rudder_plot_widget)

        # Add B_top, B_middle, and B_bottom to left_panel_B with equal height
        left_panel_B.layout().addWidget(left_panel_B_top, 1)
        left_panel_B.layout().addWidget(left_panel_B_middle, 1)
        left_panel_B.layout().addWidget(left_panel_B_bottom, 1)
        
        # Add left_panel_A and left_panel_B to left_panel with equal width
        left_panel.layout().addWidget(left_panel_A, 1)
        left_panel.layout().addWidget(left_panel_B, 1)

        # Assemble right panel with stretch ratio 1:2 (controls : reserved)
        right_panel.layout().addWidget(controls_panel, 1)
        right_panel.layout().addWidget(indicator_panel, 4)

        # Add to Live tab layout dengan rasio 3:1
        live_tab.layout().addWidget(left_panel, 3)
        live_tab.layout().addWidget(right_panel, 1)
        
        # Tab kedua "Analize Data" dibagi dua panel (rasio 3:1) seperti tab pertama
        analyze_tab = QWidget(self)
        analyze_tab.setLayout(QHBoxLayout())
        analyze_tab.layout().setContentsMargins(0, 0, 0, 0)
        
        analyze_left_panel = QWidget(self)
        analyze_left_panel.setLayout(QVBoxLayout())
        analyze_left_panel.layout().setContentsMargins(0, 0, 0, 0)
        analyze_left_panel.layout().setSpacing(12)
        
        analyze_left_panel_top = QWidget(self)
        analyze_left_panel_top.setLayout(QHBoxLayout())
        analyze_left_panel_top.layout().setContentsMargins(0, 0, 0, 0)
        analyze_left_panel_top.layout().setSpacing(0)
        
        # Sub-panel A kiri (struktur sama dengan left_panel_A di tab pertama)
        analyze_left_panel_A = QWidget(self)
        analyze_left_panel_A.setLayout(QVBoxLayout())
        analyze_left_panel_A.layout().setContentsMargins(12, 12, 12, 12)
        
        analyze_left_panel_A_top = QGroupBox("Map Viewer (Analyze)", self)
        analyze_left_panel_A_top.setLayout(QVBoxLayout())
        self.analyze_map_webview = MapWebView((self.base_lat, self.base_lon))
        analyze_left_panel_A_top.layout().addWidget(self.analyze_map_webview)
        
        analyze_left_panel_A_bottom = QGroupBox("RPM Propeller Time Series (Recorded)", self)
        analyze_left_panel_A_bottom.setLayout(QVBoxLayout())
        self.analyze_rpm_plot_widget = pg.PlotWidget()
        self.analyze_rpm_plot_widget.setLabel('left', 'RPM', color='#e5e7eb', **{'font-size': '8pt'})
        self.analyze_rpm_plot_widget.setLabel('bottom', 'Time (s)', color='#e5e7eb', **{'font-size': '8pt'})
        self.analyze_rpm_plot_widget.setBackground('#111827')
        self.analyze_rpm_plot_widget.setTitle('RPM Propeller (Recorded)', color='#e5e7eb', size='12pt')
        self.analyze_rpm_plot_widget.addLegend(offset=(10, 10))
        self.analyze_rpm_plot_widget.showGrid(x=False, y=False)
        self.analyze_rpm_plot_widget.getAxis('left').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.analyze_rpm_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.analyze_rpm_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.analyze_rpm_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.analyze_rpm1_curve = self.analyze_rpm_plot_widget.plot(name='RPM Propeller 1', pen=pg.mkPen(color='#3b82f6', width=2))
        self.analyze_rpm2_curve = self.analyze_rpm_plot_widget.plot(name='RPM Propeller 2', pen=pg.mkPen(color='#ef4444', width=2))
        self.analyze_rpm_target = pg.TargetItem(
            size=18,
            pen=pg.mkPen(color='#facc15', width=1.5),
            movable=False,
            symbol='x'
        )
        self.analyze_rpm_target.setZValue(2)
        self.analyze_rpm_plot_widget.addItem(self.analyze_rpm_target)
        self.analyze_rpm_target.hide()
        self.analyze_rpm_label = pg.TextItem(
            text='',
            color='#f9fafb',
            anchor=(0, 1)
        )
        self.analyze_rpm_label.setZValue(2)
        self.analyze_rpm_plot_widget.addItem(self.analyze_rpm_label)
        self.analyze_rpm_label.hide()
        self.analyze_rpm_hover_proxy = pg.SignalProxy(
            self.analyze_rpm_plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_analyze_rpm_mouse_moved
        )
        analyze_left_panel_A_bottom.layout().addWidget(self.analyze_rpm_plot_widget)
        
        analyze_left_panel_A.layout().addWidget(analyze_left_panel_A_top, 2)
        analyze_left_panel_A.layout().addWidget(analyze_left_panel_A_bottom, 1)
        
        # Sub-panel B kanan (struktur sama dengan left_panel_B di tab pertama)
        analyze_left_panel_B = QWidget(self)
        analyze_left_panel_B.setLayout(QVBoxLayout())
        analyze_left_panel_B.layout().setContentsMargins(12, 12, 12, 12)
        
        analyze_left_panel_B_top = QGroupBox("Roll & Pitch Time Series (Recorded)", self)
        analyze_left_panel_B_top.setLayout(QVBoxLayout())
        self.analyze_attitude_plot_widget = pg.PlotWidget()
        self.analyze_attitude_plot_widget.setLabel('left', 'Angle (°)', color='#e5e7eb', **{'font-size': '8pt'})
        self.analyze_attitude_plot_widget.setLabel('bottom', 'Time (s)', color='#e5e7eb', **{'font-size': '8pt'})
        self.analyze_attitude_plot_widget.setTitle('Roll & Pitch (Recorded)', color='#e5e7eb', size='11pt')
        self.analyze_attitude_plot_widget.setBackground('#111827')
        self.analyze_attitude_plot_widget.addLegend(offset=(10, 10))
        self.analyze_attitude_plot_widget.showGrid(x=False, y=False)
        self.analyze_attitude_plot_widget.getAxis('left').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.analyze_attitude_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.analyze_attitude_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.analyze_attitude_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.analyze_roll_curve = self.analyze_attitude_plot_widget.plot(name='Roll', pen=pg.mkPen(color='#f59e0b', width=2))
        self.analyze_pitch_curve = self.analyze_attitude_plot_widget.plot(name='Pitch', pen=pg.mkPen(color='#8b5cf6', width=2))
        self.analyze_attitude_target = pg.TargetItem(
            size=16,
            pen=pg.mkPen(color='#f97316', width=1.5),
            movable=False,
            symbol='x'
        )
        self.analyze_attitude_target.setZValue(2)
        self.analyze_attitude_plot_widget.addItem(self.analyze_attitude_target)
        self.analyze_attitude_target.hide()
        self.analyze_pitch_target = pg.TargetItem(
            size=14,
            pen=pg.mkPen(color='#06b6d4', width=1.5),
            movable=False,
            symbol='o'
        )
        self.analyze_pitch_target.setZValue(2)
        self.analyze_attitude_plot_widget.addItem(self.analyze_pitch_target)
        self.analyze_pitch_target.hide()
        self.analyze_attitude_label = pg.TextItem(
            text='',
            color='#f9fafb',
            anchor=(0, 1)
        )
        self.analyze_attitude_label.setZValue(2)
        self.analyze_attitude_plot_widget.addItem(self.analyze_attitude_label)
        self.analyze_attitude_label.hide()
        analyze_left_panel_B_top.layout().addWidget(self.analyze_attitude_plot_widget)
        
        analyze_left_panel_B_middle = QGroupBox("Yaw & Zigzag Yaw Time Series (Recorded)", self)
        analyze_left_panel_B_middle.setLayout(QVBoxLayout())
        self.analyze_yaw_plot_widget = pg.PlotWidget()
        self.analyze_yaw_plot_widget.setLabel('left', 'Yaw (°)', color='#10b981', **{'font-size': '8pt'})
        self.analyze_yaw_plot_widget.setLabel('bottom', 'Time (s)', color='#e5e7eb', **{'font-size': '8pt'})
        self.analyze_yaw_plot_widget.setTitle('Yaw & Zigzag (Recorded)', color='#e5e7eb', size='11pt')
        self.analyze_yaw_plot_widget.setBackground('#111827')
        self.analyze_yaw_plot_widget.addLegend(offset=(10, 10))
        self.analyze_yaw_plot_widget.showGrid(x=False, y=False)
        self.analyze_yaw_plot_widget.getAxis('left').setPen(pg.mkPen(color='#10b981', width=2))
        self.analyze_yaw_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.analyze_yaw_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.analyze_yaw_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.analyze_yaw_viewbox2 = pg.ViewBox()
        self.analyze_yaw_plot_widget.scene().addItem(self.analyze_yaw_viewbox2)
        self.analyze_yaw_plot_widget.getAxis('right').linkToView(self.analyze_yaw_viewbox2)
        self.analyze_yaw_viewbox2.setXLink(self.analyze_yaw_plot_widget)
        self.analyze_yaw_plot_widget.showAxis('right')
        self.analyze_yaw_plot_widget.getAxis('right').setLabel('Zigzag Yaw (°)', color='#06b6d4', **{'font-size': '8pt'})
        self.analyze_yaw_plot_widget.getAxis('right').setPen(pg.mkPen(color='#06b6d4', width=2))
        self.analyze_yaw_plot_widget.getAxis('right').setTextPen(pg.mkPen(color='#e5e7eb'))
        def _update_analyze_yaw_views():
            self.analyze_yaw_viewbox2.setGeometry(self.analyze_yaw_plot_widget.getViewBox().sceneBoundingRect())
            self.analyze_yaw_viewbox2.linkedViewChanged(
                self.analyze_yaw_plot_widget.getViewBox(),
                self.analyze_yaw_viewbox2.XAxis
            )
        _update_analyze_yaw_views()
        self.analyze_yaw_plot_widget.getViewBox().sigResized.connect(_update_analyze_yaw_views)
        self.analyze_yaw_curve = self.analyze_yaw_plot_widget.plot(name='Yaw', pen=pg.mkPen(color='#10b981', width=2))
        self.analyze_zigzag_yaw_curve = pg.PlotDataItem(name='Zigzag', pen=pg.mkPen(color='#06b6d4', width=2))
        self.analyze_yaw_viewbox2.addItem(self.analyze_zigzag_yaw_curve)
        self.analyze_yaw_target = pg.TargetItem(
            size=16,
            pen=pg.mkPen(color='#10b981', width=1.5),
            movable=False,
            symbol='x'
        )
        self.analyze_yaw_target.setZValue(2)
        self.analyze_yaw_plot_widget.addItem(self.analyze_yaw_target)
        self.analyze_yaw_target.hide()
        self.analyze_zigzag_target = pg.TargetItem(
            size=14,
            pen=pg.mkPen(color='#06b6d4', width=1.5),
            movable=False,
            symbol='o'
        )
        self.analyze_zigzag_target.setZValue(2)
        self.analyze_yaw_viewbox2.addItem(self.analyze_zigzag_target)
        self.analyze_zigzag_target.hide()
        self.analyze_yaw_label = pg.TextItem(
            text='',
            color='#f9fafb',
            anchor=(0, 1)
        )
        self.analyze_yaw_label.setZValue(2)
        self.analyze_yaw_plot_widget.addItem(self.analyze_yaw_label)
        self.analyze_yaw_label.hide()
        analyze_left_panel_B_middle.layout().addWidget(self.analyze_yaw_plot_widget)
        
        analyze_left_panel_B_bottom = QGroupBox("Rudder 1 & 2 Time Series (Recorded)", self)
        analyze_left_panel_B_bottom.setLayout(QVBoxLayout())
        self.analyze_rudder_plot_widget = pg.PlotWidget()
        self.analyze_rudder_plot_widget.setLabel('left', 'Angle (°)', color='#e5e7eb', **{'font-size': '8pt'})
        self.analyze_rudder_plot_widget.setLabel('bottom', 'Time (s)', color='#e5e7eb', **{'font-size': '8pt'})
        self.analyze_rudder_plot_widget.setTitle('Rudder (Recorded)', color='#e5e7eb', size='11pt')
        self.analyze_rudder_plot_widget.setBackground('#111827')
        self.analyze_rudder_plot_widget.addLegend(offset=(10, 10))
        self.analyze_rudder_plot_widget.showGrid(x=False, y=False)
        self.analyze_rudder_plot_widget.getAxis('left').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.analyze_rudder_plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#e5e7eb', width=1))
        self.analyze_rudder_plot_widget.getAxis('left').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.analyze_rudder_plot_widget.getAxis('bottom').setTextPen(pg.mkPen(color='#e5e7eb'))
        self.analyze_rud1_curve = self.analyze_rudder_plot_widget.plot(name='Rudder 1', pen=pg.mkPen(color='#ec4899', width=2))
        self.analyze_rud2_curve = self.analyze_rudder_plot_widget.plot(name='Rudder 2', pen=pg.mkPen(color='#14b8a6', width=2))
        self.analyze_rudder_target = pg.TargetItem(
            size=16,
            pen=pg.mkPen(color='#f472b6', width=1.5),
            movable=False,
            symbol='x'
        )
        self.analyze_rudder_target.setZValue(2)
        self.analyze_rudder_plot_widget.addItem(self.analyze_rudder_target)
        self.analyze_rudder_target.hide()
        self.analyze_rudder_label = pg.TextItem(
            text='',
            color='#f9fafb',
            anchor=(0, 1)
        )
        self.analyze_rudder_label.setZValue(2)
        self.analyze_rudder_plot_widget.addItem(self.analyze_rudder_label)
        self.analyze_rudder_label.hide()
        analyze_left_panel_B_bottom.layout().addWidget(self.analyze_rudder_plot_widget)
        
        # Data containers for Analyze tab plots
        self.analyze_rpm_time_data: list[float] = []
        self.analyze_rpm1_data: list[float] = []
        self.analyze_rpm2_data: list[float] = []
        self.analyze_attitude_time_data: list[float] = []
        self.analyze_roll_data: list[float] = []
        self.analyze_pitch_data: list[float] = []
        self.analyze_yaw_time_data: list[float] = []
        self.analyze_yaw_data: list[float] = []
        self.analyze_zigzag_yaw_data: list[float] = []
        self.analyze_map_time_data: list[float] = []
        self.analyze_rudder_time_data: list[float] = []
        self.analyze_rud1_data: list[float] = []
        self.analyze_rud2_data: list[float] = []
        self.analyze_map_coords: list[tuple[float, float]] = []
        self.analyze_heading_values: list[float] = []
        
        analyze_left_panel_B.layout().addWidget(analyze_left_panel_B_top, 1)
        analyze_left_panel_B.layout().addWidget(analyze_left_panel_B_middle, 1)
        analyze_left_panel_B.layout().addWidget(analyze_left_panel_B_bottom, 1)
        
        analyze_left_panel_top.layout().addWidget(analyze_left_panel_A, 1)
        analyze_left_panel_top.layout().addWidget(analyze_left_panel_B, 1)
        
        analyze_left_panel_bottom = QGroupBox("Timeline Control", self)
        analyze_left_panel_bottom.setLayout(QVBoxLayout())
        analyze_left_panel_bottom.layout().setContentsMargins(12, 12, 12, 12)
        analyze_left_panel_bottom.layout().setSpacing(8)
        analyze_left_panel_bottom.setStyleSheet(
            """
            QGroupBox::title { color: #ffffff; }
            """
        )
        
        self.analyze_time_slider_scale = 1000  # gunakan ms agar slider tetap integer
        self.analyze_time_slider_scale = 1000  # gunakan ms agar slider tetap integer
        self.analyze_time_slider_step = 100
        self.analyze_time_slider = QSlider(Qt.Horizontal, self)
        self.analyze_time_slider.setRange(0, 500 * self.analyze_time_slider_scale)
        self.analyze_time_slider.setSingleStep(self.analyze_time_slider_step)
        self.analyze_time_slider.setPageStep(self.analyze_time_slider_step * 5)
        self.analyze_time_slider.setValue(0)
        self.analyze_time_slider.valueChanged.connect(self._on_analyze_time_slider_changed)
        analyze_left_panel_bottom.layout().addWidget(self.analyze_time_slider)
        
        self.analyze_time_value_label = QLabel("Timestamp: 0 s", self)
        self.analyze_time_value_label.setStyleSheet("color: #e5e7eb; font-weight: 600;")
        analyze_left_panel_bottom.layout().addWidget(self.analyze_time_value_label)
        self._update_analyze_slider_display(0)
        self._hide_analyze_rpm_marker()
        self._hide_analyze_attitude_marker()
        self._hide_analyze_rudder_marker()
        
        analyze_left_panel.layout().addWidget(analyze_left_panel_top, 9)
        analyze_left_panel.layout().addWidget(analyze_left_panel_bottom, 1)
        
        analyze_right_panel = QWidget(self)
        analyze_right_panel.setLayout(QVBoxLayout())
        analyze_right_panel.layout().setContentsMargins(12, 12, 12, 12)
        
        # analyze_right_placeholder = QGroupBox("Panel Kontrol/Filter", self)
        analyze_right_placeholder = QGroupBox("", self)
        analyze_right_placeholder.setLayout(QVBoxLayout())
        self.load_csv_btn = QPushButton("Load Recorded CSV", self)
        self.load_csv_btn.clicked.connect(self.load_analyze_csv)
        analyze_right_placeholder.layout().addWidget(self.load_csv_btn)
        
        # Checkbox untuk kontrol tampilan peta (horizontal layout)
        map_checkbox_container = QGroupBox("Map Control", self)
        map_checkbox_layout = QHBoxLayout()
        map_checkbox_layout.setContentsMargins(12, 15, 12, 15)
        map_checkbox_layout.setSpacing(12)
        map_checkbox_container.setLayout(map_checkbox_layout)

        self.analyze_show_blue_line_cb = QCheckBox("Trail Line", self)
        self.analyze_show_blue_line_cb.setChecked(True)  # Default: ya
        self.analyze_show_blue_line_cb.stateChanged.connect(self.toggle_analyze_map_blue_line)
        
        self.analyze_show_red_line_cb = QCheckBox("Heading Line", self)
        self.analyze_show_red_line_cb.setChecked(False)  # Default: tidak
        self.analyze_show_red_line_cb.stateChanged.connect(self.toggle_analyze_map_red_line)

        map_checkbox_layout.addWidget(self.analyze_show_blue_line_cb)
        map_checkbox_layout.addWidget(self.analyze_show_red_line_cb)
        map_checkbox_layout.addStretch(1)
        
        analyze_right_placeholder.layout().addWidget(map_checkbox_container)
        analyze_right_placeholder.layout().addStretch(1)
        
        analyze_right_panel.layout().addWidget(analyze_right_placeholder)
        
        analyze_tab.layout().addWidget(analyze_left_panel, 4)
        analyze_tab.layout().addWidget(analyze_right_panel, 1)
        
        # Tambahkan kedua tab ke tab widget utama
        self.tab_widget.addTab(live_tab, "Live Data")
        self.tab_widget.addTab(analyze_tab, "Analize Data")
        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #374151;
                border-radius: 12px;
                background: #0f172a;
                margin-top: 6px;
            }
            QTabBar::tab {
                background: #1f2937;
                color: #d1d5db;
                padding: 8px 24px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-weight: 600;
                margin-right: 6px;
            }
            QTabBar::tab:hover {
                background: #2563eb;
                color: #f9fafb;
            }
            QTabBar::tab:selected {
                background: #3b82f6;
                color: #ffffff;
            }
            QTabBar::tab:!selected {
                color: #9ca3af;
            }
            """
        )

        # Modern UI styling
        self.setStyleSheet(
            """
            QWidget { font-family: 'Segoe UI', Arial; font-size: 11pt; }
            QGroupBox { border: 1px solid #d0d0d0; border-radius: 10px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #222; font-weight: 600; }
            QLabel { color: #333; }
            QComboBox { padding: 6px 8px; border: 1px solid #bdbdbd; border-radius: 8px; background: #fff; }
            QComboBox:focus { border: 1px solid #3b82f6; }
            QComboBox:disabled { background: #f3f4f6; color: #9ca3af; border: 1px solid #e5e7eb; }
            QPushButton { padding: 8px 12px; background-color: #3b82f6; color: #fff; border: none; border-radius: 8px; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:checked { background-color: #ef4444; }
            QPushButton:disabled { background-color: #9ca3af; color: #f3f4f6; }
            """
        )

        # Optional: dark theme for controls panel only
        controls_panel.setStyleSheet(
            """
            QGroupBox { background: #1f2937; border: 1px solid #374151; border-radius: 10px; }
            QGroupBox::title { color: #e5e7eb; }
            QLabel { color: #e5e7eb; }
            QComboBox { background: #374151; color: #e5e7eb; border: 1px solid #4b5563; }
            QComboBox:focus { border: 1px solid #60a5fa; }
            QComboBox:disabled { background: #2d3643; color: #9ca3af; border: 1px solid #3b4450; }
            QPushButton { background-color: #3b82f6; color: #fff; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:checked { background-color: #ef4444; }
            QPushButton:disabled { background-color: #6b7280; color: #d1d5db; }
            """
        )
        # Apply same dark style to reserved panel
        indicator_panel.setStyleSheet(
            """
            QGroupBox { background: #1f2937; border: 1px solid #374151; border-radius: 10px; }
            QGroupBox::title { color: #e5e7eb; }
            QLabel { color: #e5e7eb; }
            QComboBox { background: #374151; color: #e5e7eb; border: 1px solid #4b5563; }
            QComboBox:focus { border: 1px solid #60a5fa; }
            QComboBox:disabled { background: #2d3643; color: #9ca3af; border: 1px solid #3b4450; }
            QPushButton { background-color: #3b82f6; color: #fff; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:checked { background-color: #ef4444; }
            QPushButton:disabled { background-color: #6b7280; color: #d1d5db; }
            QProgressBar { background: #111827; border: 1px solid #374151; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background-color: #10b981; }
            """
        )
        # Apply dark style to analyze right panel with checkbox styling
        analyze_right_placeholder.setStyleSheet(
            """
            QGroupBox { background: #1f2937; border: 1px solid #374151; border-radius: 10px; }
            QGroupBox::title { color: #e5e7eb; }
            QLabel { color: #e5e7eb; }
            QCheckBox { color: #e5e7eb; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:unchecked { background: #374151; border: 1px solid #4b5563; border-radius: 4px; }
            QCheckBox::indicator:checked { background: #3b82f6; border: 1px solid #2563eb; border-radius: 4px; }
            QPushButton { background-color: #3b82f6; color: #fff; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:checked { background-color: #ef4444; }
            QPushButton:disabled { background-color: #6b7280; color: #d1d5db; }
            """
        )

    
    def update_indicators(self, roll: float, pitch: float, yaw: float,
                          rud1: float, rud2: float,
                          rpm1: int, rpm2: int,
                          bat1: float, bat2: float,
                          speed: float, zigzag_yaw: float = 0.0, mode_auto: int = 0, timestamp: float = 0.0):
        """
        Update semua indicators dan plots dengan data baru.
        
        Args:
            roll: Roll angle dalam derajat
            pitch: Pitch angle dalam derajat
            yaw: Yaw angle dalam derajat (0-360°)
            rud1: Rudder 1 angle dalam derajat
            rud2: Rudder 2 angle dalam derajat
            rpm1: RPM motor propeller 1
            rpm2: RPM motor propeller 2
            bat1: Tegangan baterai control (Volt)
            bat2: Tegangan baterai motor (Volt)
            speed: Kecepatan GPS (m/s)
            zigzag_yaw: Zigzag yaw offset dalam derajat (default: 0.0)
            mode_auto: Mode kontrol (0-4, default: 0)
            timestamp: Timestamp data (detik, default: 0.0)
        """
        # Dials - all use raw data
        try:
            self.roll_label.setText(f"{roll:.1f}°")
            self.pitch_label.setText(f"{pitch:.1f}°")
            self.yaw_label.setText(f"{yaw:.1f}°")
            self.zigzag_yaw_label.setText(f"{zigzag_yaw:.1f}°")
            self.rud1_label.setText(f"{rud1:.1f}°")
            self.rud2_label.setText(f"{rud2:.1f}°")
        except Exception:
            pass

        # Speed numeric label (0..5 m/s)
        try:
            sp = max(0.0, min(5.0, float(speed)))
            self.speed_label.setText(f"{sp:.2f} m/s")
        except Exception:
            pass

        # RPM numeric labels - use raw data
        try:
            self.rpm1_label.setText(f"{int(rpm1)} RPM")
            self.rpm2_label.setText(f"{int(rpm2)} RPM")
        except Exception:
            pass

        # Update RPM time series plot - use raw data
        try:
            # Append new data with serial timestamp
            self.rpm_time_data.append(timestamp)
            self.rpm1_data.append(rpm1)
            self.rpm2_data.append(rpm2)
            
            # Keep only last max_points (rolling window)
            while len(self.rpm_time_data) > self.max_points:
                self.rpm_time_data.pop(0)
                self.rpm1_data.pop(0)
                self.rpm2_data.pop(0)
            
            # Update plot curves
            self.rpm1_curve.setData(self.rpm_time_data, self.rpm1_data)
            self.rpm2_curve.setData(self.rpm_time_data, self.rpm2_data)
            
            # Debug: print data length every 100 points
            if len(self.rpm_time_data) % 100 == 0:
                print(f"[RPM Plot] Data length: {len(self.rpm_time_data)} (max: {self.max_points})")
        except Exception as e:
            print(f"[ERROR] RPM plot update failed: {e}")

        # Update Roll & Pitch time series plot - use raw data
        try:
            self.attitude_time_data.append(timestamp)
            self.roll_data.append(roll)
            self.pitch_data.append(pitch)
            
            # Keep only last max_points (rolling window)
            while len(self.attitude_time_data) > self.max_points:
                self.attitude_time_data.pop(0)
                self.roll_data.pop(0)
                self.pitch_data.pop(0)
            
            self.roll_curve.setData(self.attitude_time_data, self.roll_data)
            self.pitch_curve.setData(self.attitude_time_data, self.pitch_data)
            
            # Debug: print data length every 100 points
            if len(self.attitude_time_data) % 100 == 0:
                print(f"[Attitude Plot] Data length: {len(self.attitude_time_data)} (max: {self.max_points})")
        except Exception as e:
            print(f"[ERROR] Attitude plot update failed: {e}")

        # Update Yaw & Zigzag Yaw time series plot - use raw data
        try:
            self.yaw_time_data.append(timestamp)
            self.yaw_data.append(yaw)
            self.zigzag_yaw_data.append(zigzag_yaw)
            
            # Keep only last max_points (rolling window)
            while len(self.yaw_time_data) > self.max_points:
                self.yaw_time_data.pop(0)
                self.yaw_data.pop(0)
                self.zigzag_yaw_data.pop(0)
            
            self.yaw_curve.setData(self.yaw_time_data, self.yaw_data)
            self.zigzag_yaw_curve.setData(self.yaw_time_data, self.zigzag_yaw_data)
            
            # Debug: print data length every 100 points
            if len(self.yaw_time_data) % 100 == 0:
                print(f"[Yaw Plot] Data length: {len(self.yaw_time_data)} (max: {self.max_points})")
        except Exception as e:
            print(f"[ERROR] Yaw plot update failed: {e}")

        # Update Rudder 1 & 2 time series plot - use raw data
        try:
            self.rudder_time_data.append(timestamp)
            self.rud1_data.append(rud1)
            self.rud2_data.append(rud2)
            
            # Keep only last max_points (rolling window)
            while len(self.rudder_time_data) > self.max_points:
                self.rudder_time_data.pop(0)
                self.rud1_data.pop(0)
                self.rud2_data.pop(0)
            
            self.rud1_curve.setData(self.rudder_time_data, self.rud1_data)
            self.rud2_curve.setData(self.rudder_time_data, self.rud2_data)
            
            # Debug: print data length every 100 points
            if len(self.rudder_time_data) % 100 == 0:
                print(f"[Rudder Plot] Data length: {len(self.rudder_time_data)} (max: {self.max_points})")
        except Exception as e:
            print(f"[ERROR] Rudder plot update failed: {e}")

        # Battery numeric labels with dynamic color - LiPo 3S (3 cell)
        # LiPo 3S specs: Full=12.6V (4.2V/cell), Nominal=11.1V (3.7V/cell), Cutoff=9.0V (3.0V/cell)
        def _bat_color(voltage: float) -> str:
            # thresholds: <10.5V red, 10.5-11.5V yellow, >=11.5V green
            if voltage < 10.5:
                color = '#ef4444'  # Merah: KRITIS (≤3.5V per cell)
            elif voltage < 11.5:
                color = '#f59e0b'  # Kuning: PERINGATAN (3.5-3.83V per cell)
            else:
                color = '#10b981'  # Hijau: NORMAL (≥3.83V per cell)
            return color

        try:
            v1 = float(bat1); v2 = float(bat2)
            self.bat1_label.setText(f"{v1:.2f} V")
            self.bat2_label.setText(f"{v2:.2f} V")
            # Apply dynamic color based on voltage
            self.bat1_label.setStyleSheet(f"color: {_bat_color(v1)}; font-weight: bold; font-size: 12pt;")
            self.bat2_label.setStyleSheet(f"color: {_bat_color(v2)}; font-weight: bold; font-size: 12pt;")
        except Exception:
            pass

        # Mode Auto indicator with description and color
        mode_descriptions = {
            0: "Manual",
            1: "Turning Right",
            2: "Turning Left",
            3: "Zigzag 10",
            4: "Zigzag 20"
        }
        mode_colors = {
            0: "#6b7280",  # gray for manual
            1: "#ef4444",  # red for turning right
            2: "#3b82f6",  # blue for turning left
            3: "#f59e0b",  # amber for zigzag 10
            4: "#8b5cf6"   # purple for zigzag 20
        }
        try:
            mode_int = int(mode_auto)
            mode_text = mode_descriptions.get(mode_int, "Unknown")
            mode_color = mode_colors.get(mode_int, "#6b7280")
            self.mode_label.setText(mode_text)
            self.mode_label.setStyleSheet(f"color: {mode_color}; font-weight: bold;")
        except Exception:
            pass

    def clear_all_plots(self):
        """
        Clear semua plot data.
        
        Method ini:
        - Clear data dari semua plot (RPM, Roll/Pitch, Yaw, Rudder)
        - Reset plot curves ke empty
        - Print confirmation message
        """
        # Clear RPM plot data
        self.rpm_time_data.clear()
        self.rpm1_data.clear()
        self.rpm2_data.clear()
        self.rpm1_curve.setData([], [])
        self.rpm2_curve.setData([], [])
        
        # Clear Roll & Pitch plot data
        self.attitude_time_data.clear()
        self.roll_data.clear()
        self.pitch_data.clear()
        self.roll_curve.setData([], [])
        self.pitch_curve.setData([], [])
        
        # Clear Yaw & Zigzag Yaw plot data
        self.yaw_time_data.clear()
        self.yaw_data.clear()
        self.zigzag_yaw_data.clear()
        self.yaw_curve.setData([], [])
        self.zigzag_yaw_curve.setData([], [])
        
        # Clear Rudder 1 & 2 plot data
        self.rudder_time_data.clear()
        self.rud1_data.clear()
        self.rud2_data.clear()
        self.rud1_curve.setData([], [])
        self.rud2_curve.setData([], [])
        
        print("[PLOTS] All plots cleared")
    
    def clear_analyze_plots(self):
        """
        Clear semua data plot pada tab Analyze.
        """
        self.analyze_rpm_time_data.clear()
        self.analyze_rpm1_data.clear()
        self.analyze_rpm2_data.clear()
        self.analyze_rpm1_curve.setData([], [])
        self.analyze_rpm2_curve.setData([], [])
        
        self.analyze_attitude_time_data.clear()
        self.analyze_roll_data.clear()
        self.analyze_pitch_data.clear()
        self.analyze_roll_curve.setData([], [])
        self.analyze_pitch_curve.setData([], [])
        
        self.analyze_yaw_time_data.clear()
        self.analyze_yaw_data.clear()
        self.analyze_zigzag_yaw_data.clear()
        self.analyze_yaw_curve.setData([], [])
        self.analyze_zigzag_yaw_curve.setData([], [])
        self._hide_analyze_yaw_marker()
        
        self.analyze_rudder_time_data.clear()
        self.analyze_rud1_data.clear()
        self.analyze_rud2_data.clear()
        self.analyze_rud1_curve.setData([], [])
        self.analyze_rud2_curve.setData([], [])
        
        # Clear map overlays
        self.analyze_map_time_data.clear()
        self.analyze_map_coords.clear()
        self.analyze_heading_values.clear()
        self.analyze_map_webview.clear_markers()
        self.analyze_map_webview.trail_coords = []
        self.analyze_map_webview.marker_count = 0
        
        if hasattr(self, "analyze_time_slider"):
            max_default = 500 * (getattr(self, "analyze_time_slider_scale", 1))
            self.analyze_time_slider.setRange(0, max_default)
            self.analyze_time_slider.setValue(0)
            self._update_analyze_slider_display(0)
            self._hide_analyze_rpm_marker()
            self._hide_analyze_attitude_marker()
            self._hide_analyze_yaw_marker()
            self._hide_analyze_rudder_marker()

    def _update_analyze_slider_display(self, value: int | None = None):
        """
        Update label dan tooltip slider timeline Analyze.
        """
        if not hasattr(self, "analyze_time_slider"):
            return
        if value is None:
            value = self.analyze_time_slider.value()
        scale = getattr(self, "analyze_time_slider_scale", 1)
        seconds = value / scale if scale else float(value)
        self.analyze_time_slider.setToolTip(f"Timestamp: {seconds:.3f} s")
        if hasattr(self, "analyze_time_value_label"):
            self.analyze_time_value_label.setText(f"Timestamp: {seconds:.3f} s")
    
    def _on_analyze_time_slider_changed(self, value: int):
        """
        Pastikan slider hanya berada di kelipatan step dari nilai minimum.
        """
        if not hasattr(self, "analyze_time_slider"):
            return
        snapped_value = self._snap_analyze_slider_value(value)
        if snapped_value != value:
            self.analyze_time_slider.blockSignals(True)
            self.analyze_time_slider.setValue(snapped_value)
            self.analyze_time_slider.blockSignals(False)
        self._update_analyze_slider_display(snapped_value)
        scale = getattr(self, "analyze_time_slider_scale", 1)
        seconds = snapped_value / scale if scale else float(snapped_value)
        self._update_analyze_rpm_marker(seconds)
        self._update_analyze_attitude_marker(seconds)
        self._update_analyze_yaw_marker(seconds)
        self._update_analyze_rudder_marker(seconds)
        self._update_analyze_map_marker(seconds)
    
    def _snap_analyze_slider_value(self, value: int) -> int:
        """
        Hitung nilai slider terdekat dengan kelipatan step berbasis minimum.
        """
        if not hasattr(self, "analyze_time_slider"):
            return value
        step = getattr(self, "analyze_time_slider_step", 1)
        if step <= 0:
            return value
        slider_min = self.analyze_time_slider.minimum()
        relative = value - slider_min
        snapped_relative = round(relative / step) * step
        return slider_min + snapped_relative

    def _on_analyze_rpm_mouse_moved(self, event):
        """
        Tampilkan crosshair dan label nilai saat kursor bergerak di atas plot Analyze RPM.
        """
        if not hasattr(self, "analyze_rpm_plot_widget"):
            return
        if isinstance(event, tuple):
            event = event[0]
        scene_bounds = self.analyze_rpm_plot_widget.sceneBoundingRect()
        if event is None or not scene_bounds.contains(event):
            self.analyze_rpm_label.hide()
            self.analyze_rpm_target.hide()
            return
        mouse_point = self.analyze_rpm_plot_widget.plotItem.vb.mapSceneToView(event)
        x_val = mouse_point.x()
        y_val = mouse_point.y()
        rpm1 = self._interpolate_analyze_series_value(self.analyze_rpm_time_data, self.analyze_rpm1_data, x_val)
        rpm2 = self._interpolate_analyze_series_value(self.analyze_rpm_time_data, self.analyze_rpm2_data, x_val)
        self._display_analyze_rpm_marker(x_val, rpm1, rpm2, mouse_point.y())

    @staticmethod
    def _interpolate_analyze_series_value(time_data: list[float], value_data: list[float], x_value: float) -> float | None:
        """
        Ambil nilai pada kurva Analyze RPM terdekat dengan posisi kursor menggunakan interpolasi linear.
        """
        if not time_data or not value_data:
            return None
        index = bisect_left(time_data, x_value)
        if index <= 0:
            return value_data[0]
        if index >= len(time_data):
            return value_data[-1]
        x0 = time_data[index - 1]
        x1 = time_data[index]
        y0 = value_data[index - 1]
        y1 = value_data[index]
        if x1 == x0:
            return y0
        ratio = (x_value - x0) / (x1 - x0)
        return y0 + ratio * (y1 - y0)

    def _update_analyze_rpm_marker(self, timestamp: float | None = None):
        """
        Update posisi TargetItem Analyze RPM berdasarkan timestamp (misal dari slider).
        """
        if not hasattr(self, "analyze_rpm_plot_widget"):
            return
        if timestamp is None:
            if not hasattr(self, "analyze_time_slider"):
                return
            scale = getattr(self, "analyze_time_slider_scale", 1)
            value = self.analyze_time_slider.value()
            timestamp = value / scale if scale else float(value)
        if not self.analyze_rpm_time_data:
            self._hide_analyze_rpm_marker()
            return
        rpm1 = self._interpolate_analyze_series_value(self.analyze_rpm_time_data, self.analyze_rpm1_data, timestamp)
        rpm2 = self._interpolate_analyze_series_value(self.analyze_rpm_time_data, self.analyze_rpm2_data, timestamp)
        self._display_analyze_rpm_marker(timestamp, rpm1, rpm2, rpm1)

    def _display_analyze_rpm_marker(self, x_val: float, rpm1: float | None, rpm2: float | None, y_val: float | None):
        """
        Tampilkan marker + label Analyze RPM menggunakan nilai yang diberikan.
        """
        if not hasattr(self, "analyze_rpm_label") or not hasattr(self, "analyze_rpm_target"):
            return
        if rpm1 is None and rpm2 is None:
            self._hide_analyze_rpm_marker()
            return
        label_lines = [f"t={x_val:.3f} s"]
        if rpm1 is not None:
            label_lines.append(f"RPM1: {rpm1:.0f}")
        if rpm2 is not None:
            label_lines.append(f"RPM2: {rpm2:.0f}")
        label_text = "\n".join(label_lines)
        if y_val is None:
            y_val = rpm1 if rpm1 is not None else rpm2
        if y_val is None:
            self._hide_analyze_rpm_marker()
            return
        self.analyze_rpm_label.setText(label_text)
        self.analyze_rpm_label.setPos(x_val, y_val)
        self.analyze_rpm_label.show()
        self.analyze_rpm_target.setPos(x_val, y_val)
        self.analyze_rpm_target.show()

    def _hide_analyze_rpm_marker(self):
        """
        Sembunyikan marker & label Analyze RPM.
        """
        if hasattr(self, "analyze_rpm_label"):
            self.analyze_rpm_label.hide()
        if hasattr(self, "analyze_rpm_target"):
            self.analyze_rpm_target.hide()

    def _update_analyze_attitude_marker(self, timestamp: float | None = None):
        """
        Update posisi marker Roll/Pitch sesuai timestamp (slider Analyze).
        """
        if not hasattr(self, "analyze_attitude_plot_widget"):
            return
        if timestamp is None:
            if not hasattr(self, "analyze_time_slider"):
                return
            scale = getattr(self, "analyze_time_slider_scale", 1)
            value = self.analyze_time_slider.value()
            timestamp = value / scale if scale else float(value)
        if not self.analyze_attitude_time_data:
            self._hide_analyze_attitude_marker()
            return
        roll = self._interpolate_analyze_series_value(self.analyze_attitude_time_data, self.analyze_roll_data, timestamp)
        pitch = self._interpolate_analyze_series_value(self.analyze_attitude_time_data, self.analyze_pitch_data, timestamp)
        y_val = roll if roll is not None else pitch
        self._display_analyze_attitude_marker(timestamp, roll, pitch, y_val)

    def _display_analyze_attitude_marker(self, x_val: float, roll: float | None, pitch: float | None, y_val: float | None):
        """
        Tampilkan marker/label Roll & Pitch.
        """
        if not hasattr(self, "analyze_attitude_label") or not hasattr(self, "analyze_attitude_target"):
            return
        if roll is None and pitch is None:
            self._hide_analyze_attitude_marker()
            return
        if y_val is None:
            y_val = roll if roll is not None else pitch
        if y_val is None:
            self._hide_analyze_attitude_marker()
            return
        label_lines = [f"t={x_val:.3f} s"]
        if roll is not None:
            label_lines.append(f"Roll: {roll:.2f}°")
        if pitch is not None:
            label_lines.append(f"Pitch: {pitch:.2f}°")
        self.analyze_attitude_label.setText("\n".join(label_lines))
        self.analyze_attitude_label.setPos(x_val, y_val)
        self.analyze_attitude_label.show()
        self.analyze_attitude_target.setPos(x_val, y_val)
        self.analyze_attitude_target.show()
        if hasattr(self, "analyze_pitch_target"):
            if pitch is not None:
                self.analyze_pitch_target.setPos(x_val, pitch)
                self.analyze_pitch_target.show()
            else:
                self.analyze_pitch_target.hide()

    def _hide_analyze_attitude_marker(self):
        """
        Sembunyikan marker/label Roll & Pitch.
        """
        if hasattr(self, "analyze_attitude_label"):
            self.analyze_attitude_label.hide()
        if hasattr(self, "analyze_attitude_target"):
            self.analyze_attitude_target.hide()
        if hasattr(self, "analyze_pitch_target"):
            self.analyze_pitch_target.hide()

    def _update_analyze_yaw_marker(self, timestamp: float | None = None):
        """
        Update posisi marker Yaw & Zigzag sesuai timestamp slider Analyze.
        """
        if not hasattr(self, "analyze_yaw_plot_widget"):
            return
        if timestamp is None:
            if not hasattr(self, "analyze_time_slider"):
                return
            scale = getattr(self, "analyze_time_slider_scale", 1)
            value = self.analyze_time_slider.value()
            timestamp = value / scale if scale else float(value)
        if not self.analyze_yaw_time_data:
            self._hide_analyze_yaw_marker()
            return
        yaw_val = self._interpolate_analyze_series_value(self.analyze_yaw_time_data, self.analyze_yaw_data, timestamp)
        zigzag_val = self._interpolate_analyze_series_value(self.analyze_yaw_time_data, self.analyze_zigzag_yaw_data, timestamp)
        self._display_analyze_yaw_marker(timestamp, yaw_val, zigzag_val)

    def _display_analyze_yaw_marker(self, x_val: float, yaw_val: float | None, zigzag_val: float | None):
        """
        Tampilkan marker/label Yaw & Zigzag di tab Analyze.
        """
        has_label = hasattr(self, "analyze_yaw_label") and hasattr(self, "analyze_yaw_target")
        if not has_label:
            return
        if yaw_val is None and zigzag_val is None:
            self._hide_analyze_yaw_marker()
            return
        if yaw_val is not None:
            label_lines = [f"t={x_val:.3f} s", f"Yaw: {yaw_val:.2f}°"]
            if zigzag_val is not None:
                label_lines.append(f"Zigzag: {zigzag_val:.2f}°")
            self.analyze_yaw_label.setText("\n".join(label_lines))
            self.analyze_yaw_label.setPos(x_val, yaw_val)
            self.analyze_yaw_label.show()
            self.analyze_yaw_target.setPos(x_val, yaw_val)
            self.analyze_yaw_target.show()
        else:
            self.analyze_yaw_label.hide()
            self.analyze_yaw_target.hide()
        if hasattr(self, "analyze_zigzag_target"):
            if zigzag_val is not None:
                self.analyze_zigzag_target.setPos(x_val, zigzag_val)
                self.analyze_zigzag_target.show()
            else:
                self.analyze_zigzag_target.hide()

    def _hide_analyze_yaw_marker(self):
        """
        Sembunyikan marker/label Yaw & Zigzag.
        """
        if hasattr(self, "analyze_yaw_label"):
            self.analyze_yaw_label.hide()
        if hasattr(self, "analyze_yaw_target"):
            self.analyze_yaw_target.hide()
        if hasattr(self, "analyze_zigzag_target"):
            self.analyze_zigzag_target.hide()
    
    def _update_analyze_map_marker(self, timestamp: float | None = None):
        """
        Update posisi marker/heading di peta Analyze sesuai timestamp slider.
        """
        if not hasattr(self, "analyze_map_webview"):
            return
        if not self.analyze_map_coords:
            return
        if timestamp is None:
            if not hasattr(self, "analyze_time_slider"):
                return
            scale = getattr(self, "analyze_time_slider_scale", 1)
            value = self.analyze_time_slider.value()
            timestamp = value / scale if scale else float(value)
        time_series = self.analyze_map_time_data or self.analyze_rpm_time_data
        if not time_series:
            return
        idx = bisect_left(time_series, timestamp)
        if idx >= len(time_series):
            idx = len(time_series) - 1
        elif idx > 0 and idx < len(time_series):
            prev_time = time_series[idx - 1]
            curr_time = time_series[idx]
            if abs(timestamp - prev_time) <= abs(curr_time - timestamp):
                idx -= 1
        if idx < 0:
            idx = 0
        if idx >= len(self.analyze_map_coords):
            idx = len(self.analyze_map_coords) - 1
        coords = self.analyze_map_coords[idx]
        heading = self.analyze_heading_values[idx] if idx < len(self.analyze_heading_values) else None
        try:
            self.analyze_map_webview.move_start_marker(coords, heading, timestamp)
            self.analyze_map_webview.update_slider_heading_line(coords, heading)
        except Exception:
            pass

    def _update_analyze_rudder_marker(self, timestamp: float | None = None):
        """
        Update posisi marker Rudder 1/2 sesuai timestamp (slider Analyze).
        """
        if not hasattr(self, "analyze_rudder_plot_widget"):
            return
        if timestamp is None:
            if not hasattr(self, "analyze_time_slider"):
                return
            scale = getattr(self, "analyze_time_slider_scale", 1)
            value = self.analyze_time_slider.value()
            timestamp = value / scale if scale else float(value)
        if not self.analyze_rudder_time_data:
            self._hide_analyze_rudder_marker()
            return
        rud1 = self._interpolate_analyze_series_value(self.analyze_rudder_time_data, self.analyze_rud1_data, timestamp)
        rud2 = self._interpolate_analyze_series_value(self.analyze_rudder_time_data, self.analyze_rud2_data, timestamp)
        y_val = rud1 if rud1 is not None else rud2
        self._display_analyze_rudder_marker(timestamp, rud1, rud2, y_val)

    def _display_analyze_rudder_marker(self, x_val: float, rud1: float | None, rud2: float | None, y_val: float | None):
        """
        Tampilkan marker/label Rudder 1 & 2.
        """
        if not hasattr(self, "analyze_rudder_label") or not hasattr(self, "analyze_rudder_target"):
            return
        if rud1 is None and rud2 is None:
            self._hide_analyze_rudder_marker()
            return
        if y_val is None:
            y_val = rud1 if rud1 is not None else rud2
        if y_val is None:
            self._hide_analyze_rudder_marker()
            return
        label_lines = [f"t={x_val:.3f} s"]
        if rud1 is not None:
            label_lines.append(f"Rudder1: {rud1:.2f}°")
        if rud2 is not None:
            label_lines.append(f"Rudder2: {rud2:.2f}°")
        self.analyze_rudder_label.setText("\n".join(label_lines))
        self.analyze_rudder_label.setPos(x_val, y_val)
        self.analyze_rudder_label.show()
        self.analyze_rudder_target.setPos(x_val, y_val)
        self.analyze_rudder_target.show()

    def _hide_analyze_rudder_marker(self):
        """
        Sembunyikan marker/label Rudder 1 & 2.
        """
        if hasattr(self, "analyze_rudder_label"):
            self.analyze_rudder_label.hide()
        if hasattr(self, "analyze_rudder_target"):
            self.analyze_rudder_target.hide()

    def refresh_ports(self):
        """
        Refresh daftar port COM yang tersedia.
        
        Method ini:
        - Mendeteksi semua port COM yang tersedia
        - Update combo box dengan port yang terdeteksi
        - Auto-select port jika hanya ada satu port
        - Prefer port yang sebelumnya dipilih jika masih tersedia
        """
        current = self.port_combo.currentText() if hasattr(self, 'port_combo') else ""
        self.port_combo.clear()
        ports = list(list_ports.comports())
        items = [p.device for p in ports]
        # Prefer last used/current if still present
        self.port_combo.addItems(items)
        if current and current in items:
            self.port_combo.setCurrentText(current)
        elif len(items) == 1:
            self.port_combo.setCurrentIndex(0)
        print(f"🔌 Ports detected: {items}")

    def toggle_connection(self, checked: bool):
        if checked:
            ok = self.connect_serial()
            if not ok:
                # revert button state if failed
                self.connect_btn.setChecked(False)
        else:
            self.disconnect_serial()

    def connect_serial(self) -> bool:
        """
        Koneksi ke serial port yang dipilih.
        
        Returns:
            True jika koneksi berhasil, False jika gagal
            
        Method ini:
        - Membaca port dan baud rate dari combo box
        - Membaca map marker rate dan mengkonversi ke interval
        - Membuka serial port
        - Clear plots dan map markers
        - Start polling timer
        - Enable logging toggle
        """
        port = self.port_combo.currentText().strip()
        if not port:
            print("[SERIAL] No port selected")
            return False
        try:
            baud = int(self.baud_combo.currentText())
        except ValueError:
            baud = 115200
        
        # Read plot interval before connecting
        # Convert from "marker per detik" to "interval" (@ 10Hz sampling)
        # Formula: interval = 10 / marker_per_detik
        try:
            marker_per_detik = float(self.plot_int_combo.currentText())
            self.plot_interval = int(10.0 / marker_per_detik)
            self.plot_counter = 0  # Reset counter
        except (ValueError, ZeroDivisionError):
            self.plot_interval = 10  # Default fallback (1 marker/detik)
            self.plot_counter = 0
        
        try:
            self.ser = serial.Serial(port, baudrate=baud, timeout=0.1)
            # small delay for device ready
            QTimer.singleShot(200, lambda: None)
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
            # Clear all plots when connecting
            self.clear_all_plots()
            # Clear all markers from map when connecting
            self.map_webview.clear_markers()
            self.serial_timer.start(50)  # poll every 50 ms
            self.connect_btn.setText("Disconnect")
            print(f"[SERIAL] Connected to {port} @ {baud}")
            marker_per_detik = 10.0 / self.plot_interval
            print(f"[MAP] Map marker rate: {marker_per_detik:.1f} marker/detik (interval: {self.plot_interval} data)")
            
            # Disable controls when connected
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.plot_int_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            
            # Enable logging toggle only when connected
            if self.log_btn:
                self.log_btn.setEnabled(True)
            return True
        except Exception as e:
            print(f"[SERIAL] Connect failed: {e}")
            self.ser = None
            return False

    def disconnect_serial(self):
        """
        Putus koneksi serial port.
        
        Method ini:
        - Stop polling timer
        - Close serial port
        - Reset serial object
        - Update button text
        - Re-enable controls
        - Stop logging jika aktif
        - Disable logging toggle
        """
        try:
            if self.serial_timer.isActive():
                self.serial_timer.stop()
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        finally:
            self.ser = None
            self.connect_btn.setText("Connect")
            print("[SERIAL] Disconnected")
            
            # Re-enable controls when disconnected
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.plot_int_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            
            # stop logging if active (optional safety)
            if self.log_btn and self.log_btn.isChecked():
                self.log_btn.setChecked(False)
                self.stop_logging()
            # Disable logging toggle when disconnected
            if self.log_btn:
                self.log_btn.setEnabled(False)

    def poll_serial(self):
        """
        Poll serial port untuk membaca data baru.
        
        Method ini:
        - Membaca data dari serial port dalam buffer
        - Memproses data CSV (15 kolom)
        - Update map dengan decimation (setiap N data)
        - Update indicators untuk setiap data (real-time)
        - Append data ke log buffer jika logging aktif
        
        Format data yang diharapkan:
        timestamp,latitude,longitude,speedMps,Calc_deg_servo_1,Calc_deg_servo_2,
        roll,pitch,yaw,zigzag_yaw,rpm_prop_1,rpm_prop_2,battery_1,battery_2,mode_auto
        """
        if not self.ser:
            return
        try:
            # Buffering untuk memastikan hanya memproses baris utuh (akhiri dengan \n)
            if not hasattr(self, 'serial_buffer'):
                self.serial_buffer = b''
            available = self.ser.in_waiting
            chunk = self.ser.read(available or 1)
            if not chunk:
                return
            self.serial_buffer += chunk
            while b"\n" in self.serial_buffer:
                line, self.serial_buffer = self.serial_buffer.split(b"\n", 1)
                text = line.decode('utf-8', errors='replace').strip()
                if not text:
                    continue
                # Format target: 1854.900,-7.286621,112.796040,1.53,-3.95,7.07,3.18,62.33,98.57,0.00,463.38,2880.63,10.54,11.88
                parts = [p.strip() for p in text.split(',')]
                if len(parts) != 15:
                    # Abaikan jika kolom tidak lengkap/berlebih (menghindari baris terconcat)
                    continue
                try:
                    lat = float(parts[1])
                    lon = float(parts[2])
                    
                    # Replace 0.0, 0.0 coordinates with default location
                    if lat == 0.0 and lon == 0.0:
                        lat = -7.2854032
                        lon = 112.7902512
                    
                    # Validasi rentang lat/lon
                    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                        continue
                    speed = float(parts[3])
                    # Apply correction offset to rudder angles
                    rud1 = float(parts[4]) - self.correction_deg_servo_1
                    rud2 = float(parts[5]) - self.correction_deg_servo_2
                    roll = float(parts[6])
                    pitch = float(parts[7])
                    heading = float(parts[8])
                    zigzag_yaw = float(parts[9])*-1  # Nilai yaw zigzag dikali -1 untuk menyamakan dengan sudut rudder
                    rpm1 = int(parts[10])  # Direct integer value (no conversion)
                    rpm2 = int(parts[11])  # Direct integer value (no conversion)
                    bat1 = float(parts[12])
                    bat2 = float(parts[13])
                    mode_auto = int(parts[14]) # Mode auto dari kolom ke-15
                    timestamp = float(parts[0]) # Timestamp dari kolom ke-1
                except Exception:
                    continue
                
                # Increment plot counter
                self.plot_counter += 1
                
                # Update peta hanya setiap N data (decimation untuk performa)
                if self.plot_counter >= self.plot_interval:
                    self.map_webview.update_map((lat, lon), heading)
                    self.plot_counter = 0  # Reset counter
                
                # Update indicators tetap setiap data (real-time)
                self.update_indicators(roll, pitch, heading, rud1, rud2, rpm1, rpm2, bat1, bat2, speed, zigzag_yaw, mode_auto, timestamp)
                # Append raw CSV line to log buffer if logging enabled
                if self.log_file is not None:
                    try:
                        self.log_buffer.append(text + "\n")
                    except Exception:
                        pass
        except Exception as e:
            print(f"[SERIAL] Read error: {e}")

    def toggle_logging(self, checked: bool):
        """
        Toggle logging CSV data ke file.
        
        Args:
            checked: True untuk start logging, False untuk stop logging
            
        Method ini:
        - Meminta user memilih file CSV untuk logging
        - Menulis header CSV ke file
        - Start logging timer untuk flush buffer
        - Disable Connect/Disconnect button saat logging aktif
        """
        # Only allow logging when connected
        if checked:
            if not self.is_connected():
                # guard: should not happen since button disabled, but double-check
                self.log_btn.setChecked(False)
                return
            # choose file path
            path, _ = QFileDialog.getSaveFileName(self, "Save log CSV", "", "CSV Files (*.csv)")
            if not path:
                # cancel
                self.log_btn.setChecked(False)
                return
            try:
                self.log_file_path = path
                self.log_file = open(self.log_file_path, 'w', buffering=1, encoding='utf-8')
                # write header
                header = (
                    "timestamp (s),latitude (°),longitude (°),speedMps (m/s),Calc_deg_servo_1 (°),Calc_deg_servo_2 (°),"
                    "roll (°),pitch (°),yaw (°),zigzag_yaw (°),rpm_prop_1 (rpm),rpm_prop_2 (rpm),battery_1 (V),battery_2 (V),mode_auto\n"
                )
                self.log_file.write(header)
                self.log_buffer.clear()
                self.log_timer.start()
                self.log_btn.setText("Stop Log")
                print(f"[LOG] Start logging to {self.log_file_path}")
                # Disable Connect/Disconnect while logging
                if self.connect_btn:
                    self.connect_btn.setEnabled(False)
            except Exception as e:
                QMessageBox.critical(self, "Log Error", f"Gagal membuka file:\n{e}")
                self.log_btn.setChecked(False)
                self.log_file = None
                self.log_file_path = None
        else:
            self.stop_logging()

    def stop_logging(self):
        """
        Stop logging CSV data.
        
        Method ini:
        - Stop logging timer
        - Flush log buffer ke file
        - Close log file
        - Reset log file object
        - Update button text
        - Re-enable Connect/Disconnect button
        """
        try:
            self.log_timer.stop()
            self.flush_log_buffer()
            if self.log_file:
                self.log_file.close()
        except Exception:
            pass
        finally:
            self.log_file = None
            self.log_file_path = None
            if self.log_btn:
                self.log_btn.setText("Start Log")
            print("[LOG] Stop logging")
            # Re-enable Connect/Disconnect after logging stops
            if self.connect_btn:
                self.connect_btn.setEnabled(True)

    def flush_log_buffer(self):
        """
        Flush log buffer ke file CSV.
        
        Method ini:
        - Menulis semua data dalam buffer ke file
        - Clear buffer setelah menulis
        - Mengurangi I/O overhead dengan batch writing
        """
        if not self.log_file or not self.log_buffer:
            return
        try:
            # write and clear in batch to reduce IO overhead
            self.log_file.writelines(self.log_buffer)
            self.log_buffer.clear()
        except Exception:
            pass
    
    def load_analyze_csv(self):
        """
        Load file CSV hasil rekaman tab pertama, tampilkan di terminal,
        dan isi grafik pada tab Analyze.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Load Recorded CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as csv_file:
                csv_text = csv_file.read()
        except Exception as e:
            QMessageBox.critical(self, "Load CSV Error", f"Gagal membaca file:\n{e}")
            return
        
        # Print ulang isi file dengan format CSV original
        # print(f"[ANALYZE] Loading CSV: {path}")
        # for line in csv_text.splitlines():
        #     print(line)
        
        # Parse dan isi grafik + peta Analyze
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            if not reader.fieldnames:
                raise ValueError("Header CSV tidak ditemukan")
            
            self.clear_analyze_plots()
            
            row_count = 0
            for row in reader:
                row_count += 1
                try:
                    timestamp = float(row.get("timestamp", "0") or 0.0)
                    lat = float(row.get("latitude", "0") or 0.0)
                    lon = float(row.get("longitude", "0") or 0.0)
                    roll = float(row.get("roll", "0") or 0.0)
                    pitch = float(row.get("pitch", "0") or 0.0)
                    yaw = float(row.get("yaw", "0") or 0.0)
                    zigzag_yaw = float(row.get("zigzag_yaw", "0") or 0.0)
                    rpm1 = float(row.get("rpm_prop_1", "0") or 0.0)
                    rpm2 = float(row.get("rpm_prop_2", "0") or 0.0)
                    rud1 = float(row.get("Calc_deg_servo_1", "0") or 0.0) - self.correction_deg_servo_1
                    rud2 = float(row.get("Calc_deg_servo_2", "0") or 0.0) - self.correction_deg_servo_2
                except ValueError:
                    continue
                
                if lat == 0.0 and lon == 0.0:
                    lat = self.base_lat
                    lon = self.base_lon
                if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                    continue
                
                self.analyze_rpm_time_data.append(timestamp)
                self.analyze_rpm1_data.append(rpm1)
                self.analyze_rpm2_data.append(rpm2)
                
                self.analyze_attitude_time_data.append(timestamp)
                self.analyze_roll_data.append(roll)
                self.analyze_pitch_data.append(pitch)
                
                self.analyze_yaw_time_data.append(timestamp)
                self.analyze_yaw_data.append(yaw)
                self.analyze_zigzag_yaw_data.append(zigzag_yaw)
                
                self.analyze_rudder_time_data.append(timestamp)
                self.analyze_rud1_data.append(rud1)
                self.analyze_rud2_data.append(rud2)
                
                self.analyze_map_time_data.append(timestamp)
                self.analyze_map_coords.append((lat, lon))
                self.analyze_heading_values.append(yaw)
            
            if row_count == 0 or not self.analyze_rpm_time_data:
                print("[ANALYZE] CSV tidak memiliki baris data siap pakai.")
                return
            
            if hasattr(self, "analyze_time_slider"):
                scale = getattr(self, "analyze_time_slider_scale", 1)
                slider_min = int(self.analyze_rpm_time_data[0] * scale)
                slider_max = int(self.analyze_rpm_time_data[-1] * scale)
                if slider_min == slider_max:
                    slider_max = slider_min + 1
                self.analyze_time_slider.blockSignals(True)
                self.analyze_time_slider.setRange(slider_min, slider_max)
                self.analyze_time_slider.setValue(slider_min)
                self.analyze_time_slider.blockSignals(False)
                self._update_analyze_slider_display(slider_min)
                first_timestamp = self.analyze_rpm_time_data[0]
                self._update_analyze_rpm_marker(first_timestamp)
                self._update_analyze_attitude_marker(first_timestamp)
                self._update_analyze_yaw_marker(first_timestamp)
                self._update_analyze_rudder_marker(first_timestamp)
                self._update_analyze_map_marker(first_timestamp)
            
            self.analyze_rpm1_curve.setData(self.analyze_rpm_time_data, self.analyze_rpm1_data)
            self.analyze_rpm2_curve.setData(self.analyze_rpm_time_data, self.analyze_rpm2_data)
            
            self.analyze_roll_curve.setData(self.analyze_attitude_time_data, self.analyze_roll_data)
            self.analyze_pitch_curve.setData(self.analyze_attitude_time_data, self.analyze_pitch_data)
            
            self.analyze_yaw_curve.setData(self.analyze_yaw_time_data, self.analyze_yaw_data)
            self.analyze_zigzag_yaw_curve.setData(self.analyze_yaw_time_data, self.analyze_zigzag_yaw_data)
            
            self.analyze_rud1_curve.setData(self.analyze_rudder_time_data, self.analyze_rud1_data)
            self.analyze_rud2_curve.setData(self.analyze_rudder_time_data, self.analyze_rud2_data)
            
            if self.analyze_map_coords:
                first_coord = self.analyze_map_coords[0]
                first_heading = self.analyze_heading_values[0]
                # Recreate trail starting point
                self.analyze_map_webview.trail_coords = [first_coord]
                self.analyze_map_webview.marker_count = 0
                
                # Plot semua elemen terlebih dahulu
                self.analyze_map_webview.add_initial_marker(first_coord, first_heading)
                if first_heading is not None:
                    self.analyze_map_webview.add_heading_line_segment(first_coord, first_heading)
                
                last_coord = first_coord
                last_heading = first_heading
                for coord, heading in zip(self.analyze_map_coords[1:], self.analyze_heading_values[1:]):
                    self.analyze_map_webview.add_marker_js(coord, heading)
                    if heading is not None:
                        self.analyze_map_webview.add_heading_line_segment(coord, heading)
                    last_coord = coord
                    last_heading = heading
                
                # Apply visibility (hide trail markers by default, heading/blue per checkbox)
                self._hide_analyze_markers()
                if not self.analyze_show_blue_line_cb.isChecked():
                    self._hide_analyze_blue_line()
                if not self.analyze_show_red_line_cb.isChecked():
                    self._hide_analyze_red_line()
                
                self.analyze_map_webview.folium_map.location = last_coord
                map_name = self.analyze_map_webview.folium_map.get_name()
                self.analyze_map_webview.page().runJavaScript(f'{map_name}.setView({list(last_coord)})')
            
            print(f"[ANALYZE] Loaded {row_count} rows into graphs and map.")
        except Exception as e:
            QMessageBox.critical(self, "Load CSV Error", f"Gagal mem-parsing file:\n{e}")
    
    def toggle_analyze_map_blue_line(self, state: int):
        """Toggle visibility blue line di peta Analyze"""
        if hasattr(self, 'analyze_map_webview') and self.analyze_map_webview:
            if state == 2:  # Checked
                self._show_analyze_blue_line()
            else:  # Unchecked
                self._hide_analyze_blue_line()
    
    def toggle_analyze_map_red_line(self, state: int):
        """Toggle visibility red line heading di peta Analyze"""
        if hasattr(self, 'analyze_map_webview') and self.analyze_map_webview:
            if state == 2:  # Checked
                self._show_analyze_red_line()
            else:  # Unchecked
                self._hide_analyze_red_line()
    
    def _hide_analyze_markers(self):
        """Hide semua trail marker di peta Analyze (pointer tetap terlihat)"""
        map_name = self.analyze_map_webview.folium_map.get_name()
        js_code = f"""
        if (window.trailMarkers && typeof window.trailMarkers.eachLayer === 'function') {{
            window.trailMarkers.eachLayer(function(layer) {{
                if (layer.setOpacity) {{
                    layer.setOpacity(0);
                }}
            }});
        }}
        """
        self.analyze_map_webview.page().runJavaScript(js_code)
    
    def _hide_analyze_blue_line(self):
        """Hide blue line di peta Analyze"""
        map_name = self.analyze_map_webview.folium_map.get_name()
        js_code = f"""
        if (window.trailLine && typeof window.trailLine.setStyle === 'function') {{
            window.trailLine.setStyle({{opacity: 0}});
        }}
        """
        self.analyze_map_webview.page().runJavaScript(js_code)
    
    def _show_analyze_blue_line(self):
        """Show blue line di peta Analyze"""
        map_name = self.analyze_map_webview.folium_map.get_name()
        js_code = f"""
        if (window.trailLine && typeof window.trailLine.setStyle === 'function') {{
            window.trailLine.setStyle({{opacity: 0.8}});
            window.trailLine.bringToFront();
        }}
        """
        self.analyze_map_webview.page().runJavaScript(js_code)
    
    def _hide_analyze_red_line(self):
        """Hide red line heading di peta Analyze"""
        map_name = self.analyze_map_webview.folium_map.get_name()
        js_code = f"""
        if (window.headingLine && typeof window.headingLine.setStyle === 'function') {{
            window.headingLine.setStyle({{opacity: 0}});
        }}
        if (window.headingLineLayers && window.headingLineLayers.length) {{
            window.headingLineLayers.forEach(function(line) {{
                if (line.setStyle) {{
                    line.setStyle({{opacity: 0}});
                }}
            }});
        }}
        """
        self.analyze_map_webview.page().runJavaScript(js_code)
    
    def _show_analyze_red_line(self):
        """Show red line heading di peta Analyze (hanya yang terakhir)"""
        # Red line heading hanya menampilkan yang terakhir
        if hasattr(self, 'analyze_map_coords') and self.analyze_map_coords and hasattr(self, 'analyze_heading_values') and self.analyze_heading_values:
            js_code = f"""
            if (window.headingLine && typeof window.headingLine.setStyle === 'function') {{
                window.headingLine.setStyle({{opacity: 0.9}});
            }}
            if (window.headingLineLayers && window.headingLineLayers.length) {{
                window.headingLineLayers.forEach(function(line) {{
                    if (line.setStyle) {{
                        line.setStyle({{opacity: 0.9}});
                    }}
                }});
            }}
            """
            self.analyze_map_webview.page().runJavaScript(js_code)

    def closeEvent(self, event):
        self.disconnect_serial()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    # Start in maximized state to fit user screen
    window.showMaximized()
    sys.exit(app.exec())


