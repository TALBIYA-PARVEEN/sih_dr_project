import numpy as np

class SimulinkTelemedicineSimulator:
    def simulate(
        self,
        annual_patients=100000,
        working_days=300,
        num_phcs=25,
        bandwidth_mbps=2.0,
        ai_edge_filter_rate=0.74,
        doctor_review_time_sec=20
    ):
        daily_patients = float(annual_patients) / float(working_days)
        patients_per_phc_daily = daily_patients / float(num_phcs)

        local_cleared_daily = daily_patients * ai_edge_filter_rate
        referral_cases_daily = daily_patients * (1.0 - ai_edge_filter_rate)

        packet_size_mb = 0.65
        upload_time_per_case_sec = (packet_size_mb * 8.0) / bandwidth_mbps
        total_bandwidth_transmitted_mb = referral_cases_daily * packet_size_mb

        manual_hours_without_ai = (daily_patients * 300.0) / 3600.0
        ai_assisted_hours = (referral_cases_daily * doctor_review_time_sec) / 3600.0

        doctors_needed_without_ai = int(np.ceil(manual_hours_without_ai / 6.0))
        doctors_needed_with_ai = max(1, int(np.ceil(ai_assisted_hours / 6.0)))
        workload_reduction_pct = (1.0 - (ai_assisted_hours / max(0.01, manual_hours_without_ai))) * 100.0

        hours = [f"{h}:00" for h in range(8, 17)]
        phc_arrivals = [int(daily_patients / 9.0 * (1.0 + 0.25 * np.sin(i))) for i in range(len(hours))]
        edge_processed = [int(a * ai_edge_filter_rate) for a in phc_arrivals]
        hospital_referrals = [int(a - ep) for a, ep in zip(phc_arrivals, edge_processed)]

        return {
            "parameters": {
                "annual_patient_target": annual_patients,
                "operating_days_per_year": working_days,
                "rural_phc_count": num_phcs,
                "uplink_bandwidth_mbps": bandwidth_mbps,
                "ai_edge_triage_rate_pct": round(ai_edge_filter_rate * 100, 1),
                "doctor_review_time_sec": doctor_review_time_sec
            },
            "district_metrics": {
                "daily_screenings": round(daily_patients, 1),
                "daily_screenings_per_phc": round(patients_per_phc_daily, 1),
                "daily_edge_cleared_locally": round(local_cleared_daily, 1),
                "daily_hospital_referrals": round(referral_cases_daily, 1),
                "upload_time_per_case_seconds": round(upload_time_per_case_sec, 2),
                "total_daily_telecom_data_mb": round(total_bandwidth_transmitted_mb, 2),
            },
            "doctor_capacity_optimization": {
                "ophthalmologists_needed_without_ai": doctors_needed_without_ai,
                "ophthalmologists_needed_with_ai": doctors_needed_with_ai,
                "doctor_hours_saved_daily": round(manual_hours_without_ai - ai_assisted_hours, 1),
                "workload_reduction_percentage": round(workload_reduction_pct, 1)
            },
            "hourly_timeline_chart": {
                "hours": hours,
                "phc_patient_arrivals": phc_arrivals,
                "edge_cleared_locally": edge_processed,
                "uploaded_for_specialist_review": hospital_referrals
            }
        }
