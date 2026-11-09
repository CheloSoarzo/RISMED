-- PACS-RISMED · Repara al recibirlas las imágenes que el visor web (DICOMweb) no puede leer.
--
-- Algunos equipos (ej. lectores CR FUJIFILM, etiquetas privadas "FDMS 1.0") traen etiquetas privadas que el
-- plugin DICOMweb de Orthanc no logra convertir: la imagen se guarda bien, pero los visores OHIF y Stone fallan.
-- Este script prueba cada imagen recién llegada y, solo si falla, la vuelve a guardar sin etiquetas privadas,
-- con los mismos UID (la imagen y los datos del paciente no cambian).

function OnStoredInstance(instanceId, tags, metadata, origin)
  if origin ~= nil and origin['RequestOrigin'] == 'Lua' then
    return   -- es la copia reparada que guardó este mismo script
  end
  local st, se, sop = tags['StudyInstanceUID'], tags['SeriesInstanceUID'], tags['SOPInstanceUID']
  if st == nil or se == nil or sop == nil then
    return
  end
  local ok = pcall(RestApiGet, '/dicom-web/studies/' .. st .. '/series/' .. se .. '/instances/' .. sop .. '/metadata')
  if ok then
    return
  end
  local cmd = {}
  cmd['RemovePrivateTags'] = true
  cmd['Force'] = true
  cmd['Keep'] = { 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID' }
  local ok2, err = pcall(function()
    local reparada = RestApiPost('/instances/' .. instanceId .. '/modify', DumpJson(cmd, true), true)
    RestApiPost('/instances', reparada, true)   -- OverwriteInstances=true: reemplaza la original
  end)
  if ok2 then
    print('reparar-dicomweb: imagen ' .. sop .. ' guardada sin etiquetas privadas (el visor no podía leerla)')
  else
    print('reparar-dicomweb: no se pudo reparar ' .. sop .. ': ' .. tostring(err))
  end
end
