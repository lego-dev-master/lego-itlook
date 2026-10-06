**Lego ITlook**
# Especificación de Requerimientos de Software (SRS)
**Proyecto:** Lego ITlook  
**Versión:** 1.0  
**Fecha:** 5 de Octubre de 2026  
**Autor:** LEGO TICS SAS

## 1. Introducción

En este documento estaremos estructurando el sub módulo de mantenimineto de equipos que debe ir dentro del módulo de hojas de vida. Este módulo debe registrar las actividades de mantenimientos físicos, ya sean preventivos o correctivos para los diferentes tipos de equipos que estén asociados a un cliente. 

---

## 2. Requerimientos  
## 2.1 Desarrollo del módulo de mantenimiento de equipos.
El módulo de mantenimientos debe tener relación con el cliente y los equipos relacionados al mismo. Se debe aperturar un evento de mantenimiento para dicho equipo que contenga fecha y hora de apertura y fecha y hora de terminación.
Los eventos de mantenimiento que deben contener un Id incremental, puede tener un solo equipo o muchos equipos que pertenezcan a un cliente.
Desarrollar un campo de textos que sirva para colocar las observaciones del técnico.
Se debe contar con un estado del evento de mantenimiento que contenga las siguientes variables: Abierto, en elaboración y terminado, el campo de terminación habilitará la fecha de cierre.

## 2.2 Cargar fotos en los eventos de mantenimiento que sería un campo opcional.
Subir foto del equipo antes del mantenimiento y una foto después del mantenimiento. 
## 2.3 Bitacora de equipo
Esta nueva funcionalidad debe alimentar la bitacora del equipo, cuando se cierra un mantenimiento se deben mostrar los registros del mantenimiento. En el modulo de hojas de vida se deben eliminar las funcionalidades de registrar mantenimiento, esto con el fin de que la bitacora tome los datos provenientes del módulo de mantenimientos.
## 2.4 Reporte en PDF de un evento de mantenimiento.
Se requiere poder generar un informe en PDF que en el encabezado del documento aparezca el nombre del cliente con los datos principales del evento y posteriormente se detallen los datos de los equipos a los cuales se les hizo mantenimiento en dicho evento.  
