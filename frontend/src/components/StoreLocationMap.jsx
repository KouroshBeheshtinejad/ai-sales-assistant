import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useI18n } from '../lib/i18n'

const hasLocation = (location) => Number.isFinite(Number(location?.lat)) && Number.isFinite(Number(location?.lng))

export default function StoreLocationMap({ location, onChange, editable = false, id, ...regionProps }) {
  const { t } = useI18n()
  const mapElement = useRef(null)
  const mapRef = useRef(null)
  const markerRef = useRef(null)
  const onChangeRef = useRef(onChange)
  const [locationError, setLocationError] = useState('')
  onChangeRef.current = onChange

  const setMarker = (point, notify = false) => {
    const map = mapRef.current
    if (!map) return
    const selected = { lat: Number(point.lat.toFixed(6)), lng: Number(point.lng.toFixed(6)) }
    if (!markerRef.current) {
      markerRef.current = L.marker(point, {
        draggable: editable,
        icon: L.divIcon({ className: 'store-map-marker-icon', html: '<span></span>', iconSize: [28, 38], iconAnchor: [14, 36] }),
      }).addTo(map)
      if (editable) markerRef.current.on('dragend', (event) => {
        const { lat, lng } = event.target.getLatLng()
        onChangeRef.current?.({ lat: Number(lat.toFixed(6)), lng: Number(lng.toFixed(6)) })
      })
    } else {
      markerRef.current.setLatLng(point)
    }
    map.setView(point, Math.max(map.getZoom(), 15))
    if (notify) onChangeRef.current?.(selected)
  }

  useEffect(() => {
    if (!mapElement.current) return undefined
    const map = L.map(mapElement.current, { scrollWheelZoom: false }).setView(
      hasLocation(location) ? [Number(location.lat), Number(location.lng)] : [32, 53],
      hasLocation(location) ? 15 : 4,
    )
    mapRef.current = map
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)
    if (editable) map.on('click', (event) => setMarker(event.latlng, true))
    if (hasLocation(location)) setMarker({ lat: Number(location.lat), lng: Number(location.lng) })
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => map.invalidateSize())
    observer?.observe(mapElement.current)

    return () => {
      observer?.disconnect()
      map.remove()
      mapRef.current = null
      markerRef.current = null
    }
  }, [editable])

  useEffect(() => {
    if (!mapRef.current) return
    if (hasLocation(location)) setMarker({ lat: Number(location.lat), lng: Number(location.lng) })
    else if (markerRef.current) {
      markerRef.current.remove()
      markerRef.current = null
    }
  }, [location?.lat, location?.lng])

  const locateMe = () => {
    setLocationError('')
    if (!navigator.geolocation) {
      setLocationError(t('shop.locationError'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setMarker({ lat: coords.latitude, lng: coords.longitude }, true),
      () => setLocationError(t('shop.locationError')),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  return (
    <div id={id} className="store-location-map" {...regionProps}>
      {editable && <button type="button" className="btn btn-sm btn-secondary" onClick={locateMe}>{t('shop.useCurrentLocation')}</button>}
      {locationError && <p className="notice notice-danger" role="alert">{locationError}</p>}
      <div ref={mapElement} className="store-map-canvas" role="region" aria-label={t(editable ? 'shop.mapPickHint' : 'shop.storeInfo')} />
    </div>
  )
}