"""
Advisory engine for generating plain-language safety advice
based on earthquake and weather data.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from math import floor

logger = logging.getLogger(__name__)


class AdvisoryEngine:
    """Engine for generating safety advisories."""

    # Earthquake safety advice
    EARTHQUAKE_ADVICE = {
        'english': {
            'drop_cover_hold': "If you feel shaking, drop to the ground, take cover under a sturdy table, and hold on.",
            'strong_shaking': "Strong shaking expected - secure loose items and stay away from windows.",
            'nearby_quake': "Recent earthquake nearby - check for structural damage and avoid damaged buildings.",
            'tsunami_warning': "Tsunami warning: Coastal earthquake detected - move to higher ground if near the coast.",
            'aftershocks': "Aftershocks are likely - be prepared to drop, cover, and hold on.",
            'none': "No significant earthquake activity nearby."
        },
        'filipino': {
            'drop_cover_hold': "Kung may lumilindol, humiga sa lupa, magtago sa ilalim ng matibay na mesa, at kumapit.",
            'strong_shaking': "Inaasahan ang malakas na pagyanig - ayusin ang mga bagay na maluwag at lumayo sa mga bintana.",
            'nearby_quake': "May kaganitong lindol sa malapit - suriin ang structural damage at iwasan ang mga nasirang gusali.",
            'tsunami_warning': "Babala sa tsunami: Napansin ang lindol sa baybayin - pumunta sa mataas na lugar kung malapit sa baybayin.",
            'aftershocks': "Maaaring may mga aftershock - maging handang humiga, magtago, at kumapit.",
            'none': "Walang malapit na aktibidad ng lindol."
        }
    }

    # Weather safety advice
    WEATHER_ADVICE = {
        'english': {
            'heavy_rain': "Heavy rainfall expected - avoid flood-prone areas and don't drive through flooded roads.",
            'flood_warning': "Flood warning in effect - move to higher ground if in low-lying areas.",
            'strong_winds': "Strong winds expected - secure outdoor items and avoid being near trees or power lines.",
            'low_visibility': "Low visibility conditions - drive with caution and use headlights.",
            'extreme_heat': "Extreme heat warning - stay hydrated and avoid prolonged sun exposure.",
            'good_weather': "Weather conditions are generally safe for travel."
        },
        'filipino': {
            'heavy_rain': "Inaasahan ang malakas na pag-ulan - iwasan ang mga lugar na prone sa baha at huwag dumaan sa mga daanang baha.",
            'flood_warning': "May babala sa baha - pumunta sa mataas na lugar kung nasa mababang lugar.",
            'strong_winds': "Inaasahan ang malakas na hangin - ayusin ang mga bagay sa labas at iwasan ang paglapit sa mga puno o linya ng kuryente.",
            'low_visibility': "Mababa ang visibility - magmaneho nang maingat at gamitin ang headlights.",
            'extreme_heat': "Babala sa matinding init - uminom ng tubig at iwasan ang matagalang pagtambad sa araw.",
            'good_weather': "Ang kalagayan ng panahon ay karaniwang ligtas para sa paglalakbay."
        }
    }

    # Route safety advice
    ROUTE_ADVICE = {
        'english': {
            'hazard_detected': "Hazard detected along route - alternate route suggested.",
            'multiple_hazards': "Multiple hazards detected - alternate route strongly recommended.",
            'earthquake_risk': "Route passes near recent earthquake - proceed with caution.",
            'flood_risk': "Route passes through area with heavy rainfall - flood risk present.",
            'clear_route': "Route appears clear of significant hazards.",
            'no_hazards': "No hazards detected along route."
        },
        'filipino': {
            'hazard_detected': "May napansin na peligro sa ruta - ang alternatibong ruta ay iminumungkahi.",
            'multiple_hazards': "Maraming peligro ang napansin - malakas na inirerekumenda ang alternatibong ruta.",
            'earthquake_risk': "Ang ruta ay dumadaan sa malapit sa kaganitong lindol - magpatuloy nang may pag-iingat.",
            'flood_risk': "Ang ruta ay dumadaan sa lugar na may malakas na pag-ulan - may panganib sa baha.",
            'clear_route': "Ang ruta ay mukhang walang mga malalaking peligro.",
            'no_hazards': "Walang peligro na napansin sa ruta."
        }
    }

    @staticmethod
    def generate_earthquake_advice(
        earthquake_data: Optional[Dict[str, Any]],
        language: str = 'english'
    ) -> Dict[str, Any]:
        """Generate earthquake safety advice."""
        lang = language if language in ['english', 'filipino'] else 'english'

        if not earthquake_data or earthquake_data.get('error'):
            return {
                'summary': AdvisoryEngine.EARTHQUAKE_ADVICE[lang]['none'],
                'details': [],
                'severity': 'none'
            }

        magnitude = earthquake_data.get('magnitude', 0)
        distance_km = earthquake_data.get('distance_km', 0)
        place = earthquake_data.get('place', 'Unknown location')

        advice_list = []
        severity = 'low'

        # Magnitude-based advice
        if magnitude >= 6.0:
            advice_list.append(AdvisoryEngine.EARTHQUAKE_ADVICE[lang]['tsunami_warning'])
            severity = 'high'
        elif magnitude >= 5.0:
            advice_list.append(AdvisoryEngine.EARTHQUAKE_ADVICE[lang]['strong_shaking'])
            severity = 'medium'
        else:
            advice_list.append(AdvisoryEngine.EARTHQUAKE_ADVICE[lang]['drop_cover_hold'])

        # Distance-based advice
        if distance_km <= 25:
            advice_list.append(AdvisoryEngine.EARTHQUAKE_ADVICE[lang]['nearby_quake'])
            if magnitude >= 4.5 and severity != 'high':
                severity = 'high' if distance_km <= 10 else 'medium'

        # Always include aftershock warning for significant quakes
        if magnitude >= 4.5:
            advice_list.append(AdvisoryEngine.EARTHQUAKE_ADVICE[lang]['aftershocks'])

        # Create summary
        if magnitude > 0:
            summary = f"Magnitude {magnitude:.1f} earthquake "
            if distance_km:
                summary += f"{distance_km:.0f}km away "
            summary += f"near {place}."
        else:
            summary = "No significant earthquake activity."

        return {
            'summary': summary,
            'details': advice_list,
            'severity': severity,
            'magnitude': magnitude,
            'distance_km': distance_km
        }

    @staticmethod
    def generate_weather_advice(
        weather_data: Optional[Dict[str, Any]],
        language: str = 'english'
    ) -> Dict[str, Any]:
        """Generate weather safety advice."""
        lang = language if language in ['english', 'filipino'] else 'english'

        if not weather_data or weather_data.get('error'):
            return {
                'summary': "Weather data unavailable",
                'details': [],
                'severity': 'none'
            }

        temperature = weather_data.get('temperature')
        rainfall = weather_data.get('rain_1h', 0)
        wind_speed = weather_data.get('wind_speed', 0)
        visibility = weather_data.get('visibility', 10000)

        advice_list = []
        severity = 'low'

        # Rainfall advice
        if rainfall >= 7.5:
            advice_list.append(AdvisoryEngine.WEATHER_ADVICE[lang]['heavy_rain'])
            if rainfall >= 15:
                advice_list.append(AdvisoryEngine.WEATHER_ADVICE[lang]['flood_warning'])
                severity = 'high'
            else:
                severity = 'medium'

        # Wind advice
        if wind_speed >= 13.8:  # Near gale or stronger
            advice_list.append(AdvisoryEngine.WEATHER_ADVICE[lang]['strong_winds'])
            if wind_speed >= 20.7:  # Gale or stronger
                severity = 'high'
            elif severity != 'high':
                severity = 'medium'

        # Visibility advice
        if visibility < 1000:
            advice_list.append(AdvisoryEngine.WEATHER_ADVICE[lang]['low_visibility'])
            if visibility < 500:
                severity = 'high'
            elif severity != 'high':
                severity = 'medium'

        # Temperature advice (for Philippines context)
        if temperature:
            if temperature > 35:
                advice_list.append(AdvisoryEngine.WEATHER_ADVICE[lang]['extreme_heat'])
                severity = 'medium' if severity == 'low' else severity
            elif temperature < 15:
                advice_list.append("Unusually cool weather - wear warm clothing.")
                severity = 'low'

        # Create summary
        summary = f"{weather_data.get('weather', [{}])[0].get('description', 'Unknown conditions').title()}"

        if temperature:
            summary += f", {temperature:.1f}°C"

        if rainfall > 0:
            summary += f", {rainfall:.1f} mm/hr rain"

        if wind_speed > 5:
            summary += f", {wind_speed:.1f} m/s wind"

        # Add safe travel message if no hazards
        if not advice_list:
            advice_list.append(AdvisoryEngine.WEATHER_ADVICE[lang]['good_weather'])

        return {
            'summary': summary,
            'details': advice_list,
            'severity': severity,
            'temperature': temperature,
            'rainfall_mm_hr': rainfall,
            'wind_speed_mps': wind_speed
        }

    @staticmethod
    def generate_combined_advisory(
        earthquake_data: Optional[Dict[str, Any]],
        weather_data: Optional[Dict[str, Any]],
        language: str = 'english'
    ) -> Dict[str, Any]:
        """Generate combined safety advisory."""
        lang = language if language in ['english', 'filipino'] else 'english'

        earthquake_advice = AdvisoryEngine.generate_earthquake_advice(earthquake_data, lang)
        weather_advice = AdvisoryEngine.generate_weather_advice(weather_data, lang)

        # Determine overall severity
        severities = {'none': 0, 'low': 1, 'medium': 2, 'high': 3}
        eq_severity = severities.get(earthquake_advice['severity'], 0)
        weather_severity = severities.get(weather_advice['severity'], 0)
        overall_severity = max(eq_severity, weather_severity)

        severity_map = {0: 'none', 1: 'low', 2: 'medium', 3: 'high'}
        overall_severity_str = severity_map.get(overall_severity, 'none')

        # Combine details
        all_details = earthquake_advice['details'] + weather_advice['details']

        # Generate overall summary
        if overall_severity == 3:
            summary = "⚠️ HIGH ALERT: Multiple hazards detected. Exercise extreme caution."
        elif overall_severity == 2:
            summary = "⚠️ MODERATE ALERT: Hazard conditions present. Stay vigilant."
        elif overall_severity == 1:
            summary = "ℹ️ LOW ALERT: Minor hazards present. Remain aware."
        else:
            summary = "✅ Conditions generally safe. Maintain normal precautions."

        if lang == 'filipino':
            if overall_severity == 3:
                summary = "⚠️ MATAAS NA ALAMAT: Maraming peligro ang napansin. Mag-ingat nang labis."
            elif overall_severity == 2:
                summary = "⚠️ KATAMTAMANG ALAMAT: May mga kondisyon ng peligro. Manatiling alerto."
            elif overall_severity == 1:
                summary = "ℹ️ MABABANG ALAMAT: May mga menor na peligro. Manatiling alisto."
            else:
                summary = "✅ Karaniwang ligtas ang mga kondisyon. Panatilihin ang normal na pag-iingat."

        return {
            'overall_summary': summary,
            'overall_severity': overall_severity_str,
            'earthquake': earthquake_advice,
            'weather': weather_advice,
            'all_advice': all_details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def generate_route_advice(
        hazards_detected: bool,
        hazard_count: int,
        hazard_types: List[str],
        language: str = 'english'
    ) -> Dict[str, Any]:
        """Generate route-specific safety advice."""
        lang = language if language in ['english', 'filipino'] else 'english'

        if not hazards_detected:
            return {
                'summary': AdvisoryEngine.ROUTE_ADVICE[lang]['no_hazards'],
                'recommendation': 'proceed',
                'severity': 'none',
                'details': []
            }

        advice_list = []
        severity = 'low'

        # Check for specific hazard types
        if 'earthquake' in hazard_types:
            advice_list.append(AdvisoryEngine.ROUTE_ADVICE[lang]['earthquake_risk'])
            severity = 'medium'

        if 'flood' in hazard_types or 'rain' in hazard_types:
            advice_list.append(AdvisoryEngine.ROUTE_ADVICE[lang]['flood_risk'])
            severity = 'high' if severity != 'high' else severity

        # Generate appropriate summary based on hazard count
        if hazard_count > 1:
            summary = AdvisoryEngine.ROUTE_ADVICE[lang]['multiple_hazards']
            severity = 'high'
        else:
            summary = AdvisoryEngine.ROUTE_ADVICE[lang]['hazard_detected']
            severity = 'medium'

        recommendation = 'avoid' if severity in ['medium', 'high'] else 'proceed_with_caution'

        return {
            'summary': summary,
            'recommendation': recommendation,
            'severity': severity,
            'hazard_count': hazard_count,
            'hazard_types': hazard_types,
            'details': advice_list
        }


# Test the advisory engine
if __name__ == '__main__':
    print("Testing advisory engine...")

    # Test earthquake advice
    test_quake = {
        'magnitude': 5.5,
        'distance_km': 15.0,
        'place': 'Mindoro, Philippines'
    }

    print("\n1. English earthquake advice:")
    eq_advice_en = AdvisoryEngine.generate_earthquake_advice(test_quake, 'english')
    print(f"   Summary: {eq_advice_en['summary']}")
    print(f"   Details: {eq_advice_en['details']}")

    print("\n2. Filipino earthquake advice:")
    eq_advice_fil = AdvisoryEngine.generate_earthquake_advice(test_quake, 'filipino')
    print(f"   Summary: {eq_advice_fil['summary']}")

    # Test weather advice
    test_weather = {
        'temperature': 28.5,
        'rain_1h': 8.5,
        'wind_speed': 5.2,
        'visibility': 5000,
        'weather': [{'description': 'heavy rain'}]
    }

    print("\n3. English weather advice:")
    weather_advice_en = AdvisoryEngine.generate_weather_advice(test_weather, 'english')
    print(f"   Summary: {weather_advice_en['summary']}")
    print(f"   Details: {weather_advice_en['details']}")

    # Test combined advisory
    print("\n4. Combined advisory (English):")
    combined = AdvisoryEngine.generate_combined_advisory(test_quake, test_weather, 'english')
    print(f"   Overall: {combined['overall_summary']}")
    print(f"   Severity: {combined['overall_severity']}")

    print("\n5. Route advice with hazards:")
    route_advice = AdvisoryEngine.generate_route_advice(
        hazards_detected=True,
        hazard_count=2,
        hazard_types=['earthquake', 'flood'],
        language='english'
    )
    print(f"   Summary: {route_advice['summary']}")
    print(f"   Recommendation: {route_advice['recommendation']}")