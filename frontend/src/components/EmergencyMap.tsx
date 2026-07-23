import { useEffect, useRef, useState } from "react";
import type { HospitalRoute, RouteSnapshot } from "../api/routing";
import type { HospitalCandidate } from "../types/hospital";
import type { PatientEvent } from "../types/patient";
import type { RecommendationResult } from "../types/recommendation";

type Props = {
  patient: PatientEvent | null;
  hospitals: HospitalCandidate[];
  recommendation: RecommendationResult | null;
  route: RouteSnapshot | null;
  routes: HospitalRoute[];
  selectedHospitalId: string | null;
  onSelectHospital: (hospitalId: string) => void;
};

function escapeHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (character) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;",
    };
    return entities[character] ?? character;
  });
}

function formatDuration(seconds: number): string {
  return `${Math.max(1, Math.round(seconds / 60))}분`;
}

export default function EmergencyMap({
  patient,
  hospitals,
  recommendation,
  route,
  routes,
  selectedHospitalId,
  onSelectHospital,
}: Props) {
  const mapClientId = import.meta.env.VITE_NAVER_MAP_CLIENT_ID as string | undefined;
  const mapElement = useRef<HTMLDivElement>(null);
  const mapRef = useRef<NaverMapInstance | null>(null);
  const overlays = useRef<NaverOverlay[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => {
    if (!patient) mapRef.current = null;
  }, [patient]);

  useEffect(() => {
    if (!mapClientId) {
      setMapLoaded(false);
      return;
    }
    const registeredHost = `${window.location.protocol}//${window.location.hostname}`;
    const authFailure = (): void => {
      setMapLoaded(false);
      setMapError(
        `네이버 지도 인증에 실패했습니다. Web 서비스 URL에 ${registeredHost}을 포트와 경로 없이 등록해주세요.`,
      );
    };
    window.navermap_authFailure = authFailure;
    setMapError(null);
    if (window.naver?.maps) {
      setMapLoaded(true);
      return () => {
        if (window.navermap_authFailure === authFailure) window.navermap_authFailure = undefined;
      };
    }
    const existing = document.getElementById("naver-map-sdk");
    const script = existing instanceof HTMLScriptElement ? existing : document.createElement("script");
    if (!(existing instanceof HTMLScriptElement)) {
      script.id = "naver-map-sdk";
      script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(mapClientId)}`;
      script.async = true;
      document.head.appendChild(script);
    }
    const timeout = window.setTimeout(() => {
      if (!window.naver?.maps) setMapError("네이버 지도 SDK 응답 제한 시간을 초과했습니다.");
    }, 8_000);
    script.onload = () => {
      window.clearTimeout(timeout);
      if (window.naver?.maps) setMapLoaded(true);
      else setMapError("네이버 지도 SDK 객체를 초기화할 수 없습니다.");
    };
    script.onerror = () => {
      window.clearTimeout(timeout);
      setMapError("네이버 지도 SDK를 불러오지 못했습니다. API 권한과 등록 URL을 확인해주세요.");
    };
    return () => {
      window.clearTimeout(timeout);
      script.onload = null;
      script.onerror = null;
      if (window.navermap_authFailure === authFailure) window.navermap_authFailure = undefined;
    };
  }, [mapClientId]);

  useEffect(() => {
    const latitude = patient?.location.latitude;
    const longitude = patient?.location.longitude;
    if (
      !mapLoaded
      || !mapElement.current
      || latitude === null
      || latitude === undefined
      || longitude === null
      || longitude === undefined
      || !window.naver?.maps
    ) return;
    const center = new window.naver.maps.LatLng(latitude, longitude);
    if (!mapRef.current) {
      mapRef.current = new window.naver.maps.Map(mapElement.current, { center, zoom: 12 });
    } else {
      mapRef.current.setCenter(center);
    }
  }, [mapLoaded, patient?.location.latitude, patient?.location.longitude]);

  useEffect(() => {
    const latitude = patient?.location.latitude;
    const longitude = patient?.location.longitude;
    const map = mapRef.current;
    const naver = window.naver;
    if (
      !map
      || !naver?.maps
      || latitude === null
      || latitude === undefined
      || longitude === null
      || longitude === undefined
    ) return;
    overlays.current.forEach((overlay) => {
      overlay.close?.();
      overlay.setMap?.(null);
    });
    overlays.current = [];
    const addOverlay = (overlay: NaverOverlay): void => {
      overlays.current.push(overlay);
    };
    const center = new naver.maps.LatLng(latitude, longitude);
    const bounds = new naver.maps.LatLngBounds();
    bounds.extend(center);
    addOverlay(new naver.maps.Marker({
      position: center,
      map,
      title: "환자 위치",
      icon: {
        content: '<div class="map-marker patient-marker">119</div>',
        anchor: new naver.maps.Point(15, 15),
      },
    }));

    const routeByHospital = new Map(routes.map((item) => [item.hospital_id, item.route]));
    hospitals.forEach((hospital) => {
      const hospitalLatitude = hospital.location.latitude;
      const hospitalLongitude = hospital.location.longitude;
      if (hospitalLatitude === null || hospitalLongitude === null) return;
      const position = new naver.maps.LatLng(hospitalLatitude, hospitalLongitude);
      bounds.extend(position);
      const isSelected = hospital.hospital_id === selectedHospitalId;
      const hospitalRoute = routeByHospital.get(hospital.hospital_id);
      const marker = new naver.maps.Marker({
        position,
        map,
        title: hospital.hospital_name,
        icon: {
          content: `<div class="map-marker hospital-marker${isSelected ? " selected" : ""}">${isSelected ? "★" : "H"}</div>`,
          anchor: new naver.maps.Point(14, 14),
        },
      });
      const infoWindow = new naver.maps.InfoWindow({
        content: `<div class="map-info"><strong>${escapeHtml(hospital.hospital_name)}</strong><span>${hospitalRoute ? formatDuration(hospitalRoute.duration_seconds) : "경로 확인 전"}</span></div>`,
      });
      naver.maps.Event.addListener(marker, "click", () => {
        onSelectHospital(hospital.hospital_id);
        infoWindow.open(map, marker);
      });
      addOverlay(marker);
      addOverlay(infoWindow);
    });

    if (route?.path && route.path.length >= 2) {
      addOverlay(new naver.maps.Polyline({
        map,
        path: route.path.map(([routeLongitude, routeLatitude]) => (
          new naver.maps.LatLng(routeLatitude, routeLongitude)
        )),
        strokeColor: "#1769e8",
        strokeOpacity: 0.92,
        strokeWeight: 6,
      }));
    }
    map.fitBounds(bounds, 48);
    return () => {
      overlays.current.forEach((overlay) => {
        overlay.close?.();
        overlay.setMap?.(null);
      });
      overlays.current = [];
    };
  }, [patient, hospitals, recommendation, route, routes, selectedHospitalId, onSelectHospital]);

  if (!mapClientId) {
    return <section className="map-card map-empty"><div className="empty-icon">⌖</div><h2>지도 API 설정 필요</h2><p>VITE_NAVER_MAP_CLIENT_ID와 Web 서비스 URL을 설정해야 실제 지도를 표시합니다.</p></section>;
  }
  if (!patient) {
    return <section className="map-card map-empty"><div className="empty-icon">⌖</div><h2>환자 위치 대기 중</h2><p>채팅 확인 입력이 완료되면 공식 응급기관과 실제 경로를 표시합니다.</p></section>;
  }
  if (patient.location.latitude === null || patient.location.longitude === null) {
    return <section className="map-card map-empty"><div className="empty-icon">⌖</div><h2>좌표 확인 필요</h2><p>주소 좌표를 확인하지 못해 지도를 표시하지 않습니다.</p></section>;
  }

  return (
    <section className="map-card">
      <div className="map-toolbar">
        <strong>실시간 이송 경로</strong>
        <span>{hospitals.length}개 공식 후보</span>
        <span>{routes.length}개 실제 경로</span>
      </div>
      {mapError && <div className="map-alert">{mapError}</div>}
      <div ref={mapElement} className="map-canvas" aria-label="환자와 병원 위치 지도" />
    </section>
  );
}
