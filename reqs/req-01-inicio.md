**Lego ITlook**
# Especificación de Requerimientos de Software (SRS)
**Proyecto:** Lego ITlook  
**Versión:** 1.0  
**Fecha:** 8 de Agosto de 2026  
**Autor:** LEGO TICS SAS

## 1. Introducción

Vamos a desarrollar una aplicación web para la gestión de servicios técnicos de tecnología. En donde necesitamos gestionar Clientes, Hojas de vida de equipos, datos de licenciamiento Microsoft con control de fechas de vencimiento  por cliente y tickets de servicio. 

## 2. Objetivo

Desarrollar e implementar un sistema centralizado e intuitivo que optimice la operación de soporte e infraestructura de TI, reduciendo tiempos de atención mediante la gestión eficiente de tickets y evitando interrupciones de servicio por vencimiento de licencias.

---

## 3. Alcance del Sistema (Scope)

El sistema **Lego ITlook** abarcará los siguientes módulos funcionales principales:
* **Módulo de Clientes:** Gestión de empresas/contactos, ubicaciones y acuerdos de servicio.
* **Módulo de Hojas de Vida de Equipos:** Registro técnico detallado de hardware, software instalado, garantías y mantenimientos preventivos/correctivos.
* **Módulo de Licenciamiento Microsoft:** Inventario de licencias (M365, Azure, Windows Server, Office), asignación a usuarios/clientes y motor de notificaciones proactivas por vencimiento.
* **Módulo de Tickets de Servicio:** Ciclo de vida completo del soporte (creación, asignación, SLA, estados, historial de intervenciones y resolución).

*Nota fuera de alcance (Out of Scope v1.0): Facturación electrónica automatizada e integración directa con pasarelas de pago.*

---

## 4. Requerimientos Funcionales (RF)

Los requerimientos funcionales definen los comportamientos específicos que el sistema debe ejecutar.

### 4.1 Módulo de Clientes
* **RF-01 (Gestión de Clientes):** El sistema debe permitir crear, editar, consultar y deshabilitar clientes (razón social, NIT, contactos principales, direcciones).
* **RF-02 (Sede/Ubicaciones):** Un cliente debe poder tener múltiples sedes o departamentos asociados.

### 4.2 Módulo de Hojas de Vida de Equipos
* **RF-03 (Registro de Activos):** El sistema debe registrar equipos con datos obligatorios: código interno/serial, tipo (servidor, PC, laptop, switch, etc.), marca, modelo, especificaciones (CPU, RAM, disco) y estado operativo.
* **RF-04 (Trazabilidad de Mantenimientos):** Permite registrar bitácoras de mantenimiento asociadas al equipo, adjuntando soporte fotográfico o PDFs.

### 4.3 Módulo de Licenciamiento Microsoft
* **RF-05 (Control de Licencias):** Registrar tipo de suscripción (ej. M365 Business Premium), cantidad de licencias, fechas de adquisición y vencimiento por cliente.
* **RF-06 (Alertas de Vencimiento):** El sistema enviará notificaciones por correo electrónico a los administradores 30, 15 y 5 días antes del vencimiento de una licencia.
* **RF-07 (Modificación de modelo de licenciamiento):** Agregar los siguientes campos al registro de licencias:

usuario de instalacion varchar(100),
clave varchar(100),
codig de activacion varchar(100),
link de descarga varchar(200),

Agregar una lista en donde se puedan colocar los nombres de los usuarios que usan esas lincencias, el campo puede ser varchar(200)

### 4.4 Módulo de Tickets de Servicio
* **RF-07 (Gestión de Tickets):** Permitir la creación de tickets clasificados por prioridad (Baja, Media, Alta, Crítica) y tipo de servicio (Soporte, Mantenimiento, Proyecto).
* **RF-08 (Asignación y SLA):** Asignar técnicos responsables a cada ticket y monitorear el tiempo de respuesta acorde al Acuerdo de Nivel de Servicio (SLA) configurado.

---

## 5. Requerimientos No Funcionales (RNF)

Los requerimientos no funcionales especifican los atributos de calidad y restricciones del sistema.

* **RNF-01 (Seguridad & Roles):** Control de acceso basado en roles (RBAC): Administrador, Técnico. Autenticación segura mediante JWT o OAuth2. el cliente no tiene acceso a la plataforma solo los técnicos internos.
* **RNF-02 (Rendimiento):** El tiempo de respuesta de las peticiones en el panel principal no debe exceder los 2 segundos para cargas estándar.
* **RNF-03 (Disponibilidad):** La plataforma debe asegurar un uptime del 99.5% mensual.
* **RNF-04 (Usabilidad & Responsividad):** La interfaz debe ser intuitiva y adaptable a dispositivos móviles (Web Responsive) para técnicos en campo.

---

## 6. Arquitectura y Stack Tecnológico Propuesto

* **Frontend:** Framework moderno FLASK con interfaz limpia e intuitiva usando HTML5, BOOTSTRAP 5 y JavaScript.
* **Backend:** FRAMEWORK FLASK PYTHON .
* **Base de Datos:** PostgreSQL.
* **Infraestructura:** Despliegue mediante contenedores **Docker** sobre servidor Linux.


