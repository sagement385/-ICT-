declare global {
  interface NaverLatLng {}
  interface NaverLatLngBounds {
    extend(position: NaverLatLng): void;
  }
  interface NaverMapInstance {
    setCenter(position: NaverLatLng): void;
    fitBounds(bounds: NaverLatLngBounds, margin?: number): void;
  }
  interface NaverOverlay {
    setMap?(map: NaverMapInstance | null): void;
    close?(): void;
  }
  interface NaverMarker extends NaverOverlay {}
  interface NaverInfoWindow extends NaverOverlay {
    open(map: NaverMapInstance, marker: NaverMarker): void;
  }
  interface NaverMapsApi {
    LatLng: new (latitude: number, longitude: number) => NaverLatLng;
    LatLngBounds: new () => NaverLatLngBounds;
    Point: new (x: number, y: number) => object;
    Map: new (
      element: HTMLElement,
      options: { center: NaverLatLng; zoom: number },
    ) => NaverMapInstance;
    Marker: new (options: Record<string, unknown>) => NaverMarker;
    InfoWindow: new (options: { content: string }) => NaverInfoWindow;
    Polyline: new (options: Record<string, unknown>) => NaverOverlay;
    Event: {
      addListener(target: object, eventName: string, callback: () => void): object;
    };
  }
  interface Window {
    naver?: { maps: NaverMapsApi };
    navermap_authFailure?: () => void;
  }
}

export {};
