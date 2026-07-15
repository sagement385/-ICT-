import { useEffect, useRef, useState } from "react";
import type { HospitalRoute, RouteSnapshot } from "../api/routing";
import type { Hospital } from "../types/hospital";
import type { PatientEvent } from "../types/patient";
import type { RecommendationResult } from "../types/recommendation";

type Props = {
  patient: PatientEvent | null;
  hospitals: Hospital[];
  recommendation: RecommendationResult | null;
  route: RouteSnapshot | null;
  routes: HospitalRoute[];
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
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `${minutes}분`;
}

export default function EmergencyMap({ patient, hospitals, recommendation, route, routes }: Props) {
  const mapClientId = import.meta.env.VITE_NAVER_MAP_CLIENT_ID as string | undefined;
  const mapElement = useRef<HTMLDivElement>(null);
  const overlays = useRef<any[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [selectedHospitalId, setSelectedHospitalId] = useState<string | null>(null);

  useEffect(() => {
    if (!mapClientId) {
      setMapLoaded(false);
      return;
    }
    const registeredHost = `${window.location.protocol}//${window.location.hostname}`;
    const authFailure = (): void => {
      setMapLoaded(false);
      setMapError(
        `네이버 지도 인증에 실패했습니다. Maps Application에서 Web Dynamic Map을 선택하고 Web 서비스 URL에 ${registeredHost}을 포트와 경로 없이 등록한 뒤 새로고침해주세요.`,
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

    const foundScript = document.getElementById("naver-map-sdk");
    const existingScript = foundScript instanceof HTMLScriptElement
      && foundScript.src.includes("ncpKeyId=")
      ? foundScript
      : null;
    if (foundScript && existingScript === null) foundScript.remove();
    const script = existingScript
      ? existingScript
      : document.createElement("script");
    script.id = "naver-map-sdk";
    script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(mapClientId)}`;
    script.async = true;
    script.onload = () => {
      if (window.naver?.maps) {
        setMapLoaded(true);
      } else {
        setMapError("네이버 지도 SDK가 로드됐지만 지도 객체를 초기화할 수 없습니다.");
      }
    };
    script.onerror = () => {
      setMapError("네이버 지도 SDK를 불러오지 못했습니다. Web 서비스 URL 등록과 API 권한을 확인해주세요.");
    };
    if (!existingScript) document.head.appendChild(script);
    return () => {
      script.onload = null;
      script.onerror = null;
      if (window.navermap_authFailure === authFailure) window.navermap_authFailure = undefined;
    };
  }, [mapClientId]);

  useEffect(() => {
    const latitude = patient?.location.latitude;
    const longitude = patient?.location.longitude;
    if (!mapLoaded || !mapElement.current || latitude === null || latitude === undefined || longitude === null || longitude === undefined) return;
    if (!window.naver?.maps) {
      setMapError("네이버 지도 SDK를 사용할 수 없습니다.");
      return;
    }

    const naver = window.naver;
    const center = new naver.maps.LatLng(latitude, longitude);
    const map = new naver.maps.Map(mapElement.current, { center, zoom: 12 });
    overlays.current.forEach((overlay) => overlay.setMap?.(null));
    overlays.current = [];

    const addOverlay = (overlay: any): void => {
      overlays.current.push(overlay);
    };

    const patientMarker = new naver.maps.Marker({
      position: center,
      map,
      title: "환자 위치",
      icon: {
        content: '<div style="width:28px;height:28px;border-radius:50%;background:#e6283f;border:3px solid #fff;box-shadow:0 2px 8px #243b5a66;color:#fff;font-weight:800;font-size:11px;display:grid;place-items:center">119</div>',
        anchor: new naver.maps.Point(14, 14),
      },
    });
    addOverlay(patientMarker);

    const routeByHospital = new Map(routes.map((item) => [item.hospital_id, item.route]));
    const activeHospitalId = selectedHospitalId
      ?? recommendation?.recommended_hospitals[0]?.hospital_id
      ?? routes[0]?.hospital_id
      ?? (routes.length === 0 && route ? "__single_route__" : undefined);
    const bounds = new naver.maps.LatLngBounds();
    bounds.extend(center);

    hospitals.forEach((hospital) => {
      const hospitalLatitude = hospital.location.latitude;
      const hospitalLongitude = hospital.location.longitude;
      if (hospitalLatitude === null || hospitalLongitude === null) return;
      const position = new naver.maps.LatLng(hospitalLatitude, hospitalLongitude);
      bounds.extend(position);
      const hospitalRoute = routeByHospital.get(hospital.hospital_id);
      const infoText = hospitalRoute
        ? `${escapeHtml(hospital.hospital_name)} · ${formatDuration(hospitalRoute.duration_seconds)}`
        : escapeHtml(hospital.hospital_name);
      const marker = new naver.maps.Marker({
        position,
        map,
        title: hospital.hospital_name,
        icon: hospital.hospital_id === activeHospitalId
          ? {
              content: '<div style="width:26px;height:26px;border-radius:50%;background:#2461dc;border:3px solid #fff;box-shadow:0 2px 8px #243b5a66;color:#fff;font-weight:800;display:grid;place-items:center">★</div>',
              anchor: new naver.maps.Point(13, 13),
            }
          : undefined,
      });
      addOverlay(marker);
      const infoWindow = new naver.maps.InfoWindow({
        content: `<div style="padding:10px;font-size:12px;white-space:nowrap">${infoText}</div>`,
      });
      naver.maps.Event.addListener(marker, "click", () => {
        setSelectedHospitalId(hospital.hospital_id);
        infoWindow.open(map, marker);
      });
      addOverlay(infoWindow);
    });

    const drawRoute = (hospitalId: string, routeSnapshot: RouteSnapshot): void => {
      if (!routeSnapshot.path || routeSnapshot.path.length < 2) return;
      const isActive = hospitalId === activeHospitalId;
      const polyline = new naver.maps.Polyline({
        map,
        path: routeSnapshot.path.map(([routeLongitude, routeLatitude]) => new naver.maps.LatLng(routeLatitude, routeLongitude)),
        strokeColor: isActive ? "#2563eb" : "#7f9bc7",
        strokeOpacity: isActive ? 0.95 : 0.55,
        strokeWeight: isActive ? 6 : 4,
      });
      addOverlay(polyline);
    };

    routes.forEach((item) => drawRoute(item.hospital_id, item.route));
    if (routes.length === 0 && route) drawRoute("__single_route__", route);
    map.fitBounds(bounds, 40);
    return () => {
      overlays.current.forEach((overlay) => overlay.setMap?.(null));
      overlays.current = [];
    };
  }, [mapLoaded, patient?.location.latitude, patient?.location.longitude, hospitals, recommendation, route, routes, selectedHospitalId]);

  if (!mapClientId) {
    return <section className="map-card map-empty"><div className="empty-icon">⌖</div><h2>지도 API 설정 필요</h2><p>VITE_NAVER_MAP_CLIENT_ID와 Web 서비스 URL이 설정되면 실제 환자 위치와 병원 마커를 표시합니다.</p></section>;
  }
  if (!patient) {
    return <section className="map-card map-empty"><div className="empty-icon">⌖</div><h2>환자 위치 대기 중</h2><p>채팅 입력이 완료되면 지도와 실제 병원 위치를 표시합니다.</p></section>;
  }
  if (patient.location.latitude === null || patient.location.longitude === null) {
    return <section className="map-card map-empty"><div className="empty-icon">⌖</div><h2>좌표 확인 필요</h2><p>주소 좌표를 확인하지 못해 지도를 표시하지 않습니다.</p></section>;
  }

  return (
    <section className="map-card">
      <div className="map-toolbar">
        <strong>지도</strong>
        <span>{hospitals.length}개 실제 병원 후보</span>
        <span>{routes.length}개 실제 경로</span>
      </div>
      {mapError ? <div className="map-error">{mapError}</div> : <div ref={mapElement} className="map-canvas" />}
    </section>
  );
}
