# ... (all existing imports)
from surveillance_detector import SurveillanceDetector, load_appearances_from_kismet
from gps_tracker import GPSTracker, KMLExporter, simulate_gps_data
from secure_credentials import secure_config_loader
from report_generator import ReportGenerator # NEW: Import the new class

# ... (logging configuration)

class SurveillanceAnalyzer:
    # ... (__init__ remains the same)
    
    def analyze_kismet_data(self, kismet_db_path: str = None, 
                          gps_data: list = None) -> dict:
        # ... (all data loading logic remains the same up until report generation)
        
        # Perform surveillance detection
        print("\n🚨 Analyzing for surveillance patterns...")
        suspicious_devices = self.detector.analyze_surveillance_patterns()
        
        # ... (printing summary of suspicious devices remains the same)

        # --- CHANGED: Report Generation Logic ---
        # Generate reports using the new dedicated reporter class
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = "surveillance_reports"
        kml_dir = "kml_files"
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(kml_dir, exist_ok=True)

        report_file = os.path.join(reports_dir, f"surveillance_report_{timestamp}.md")
        
        print(f"\n📝 Generating surveillance reports:")
        
        # Instantiate the new reporter with the analysis results
        reporter = ReportGenerator(
            suspicious_devices=suspicious_devices,
            all_appearances=self.detector.appearances,
            device_history=self.detector.device_history,
            thresholds=self.detector.thresholds
        )
        
        # Generate the report
        surveillance_report = reporter.generate_surveillance_report(report_file)
        
        # ... (rest of the analysis, KML generation, and results dictionary remains the same)
        # Make sure to update the call to generate_surveillance_report if it was different
        # For example, if it generated HTML, that logic is now inside the reporter.

        return results
    
    # ... (all other methods in SurveillanceAnalyzer remain the same)

# ... (main function remains the same)