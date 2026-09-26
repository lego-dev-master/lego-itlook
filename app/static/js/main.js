document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // Dynamic Client -> Location / Contact / Asset dropdown loader
  const clientSelect = document.getElementById('client_id');
  const locationSelect = document.getElementById('location_id');
  const contactSelect = document.getElementById('contact_id');
  const assetSelect = document.getElementById('asset_id');

  if (clientSelect) {
    clientSelect.addEventListener('change', function () {
      const clientId = this.value;
      
      if (locationSelect) {
        locationSelect.innerHTML = '<option value="">Cargando sedes...</option>';
        if (clientId) {
          fetch(`/clients/api/${clientId}/locations`)
            .then(res => res.json())
            .then(data => {
              locationSelect.innerHTML = '<option value="">-- Seleccionar Sede (Opcional) --</option>';
              data.forEach(loc => {
                const opt = document.createElement('option');
                opt.value = loc.id;
                opt.textContent = loc.name;
                locationSelect.appendChild(opt);
              });
            })
            .catch(err => {
              console.error('Error fetching locations:', err);
              locationSelect.innerHTML = '<option value="">Error al cargar sedes</option>';
            });
        } else {
          locationSelect.innerHTML = '<option value="">-- Seleccionar Sede (Opcional) --</option>';
        }
      }

      if (contactSelect) {
        contactSelect.innerHTML = '<option value="">Cargando contactos...</option>';
        if (clientId) {
          fetch(`/clients/api/${clientId}/contacts`)
            .then(res => res.json())
            .then(data => {
              contactSelect.innerHTML = '<option value="">-- Seleccionar Contacto Solicitante --</option>';
              data.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = `${c.name} (${c.email})${c.is_primary ? ' [Principal]' : ''}`;
                if (c.is_primary) opt.selected = true;
                contactSelect.appendChild(opt);
              });
            })
            .catch(err => {
              console.error('Error fetching contacts:', err);
              contactSelect.innerHTML = '<option value="">Error al cargar contactos</option>';
            });
        } else {
          contactSelect.innerHTML = '<option value="">-- Seleccionar Contacto Solicitante --</option>';
        }
      }

      if (assetSelect) {
        assetSelect.innerHTML = '<option value="">Cargando equipos...</option>';
        if (clientId) {
          fetch(`/assets/api/${clientId}/assets`)
            .then(res => res.json())
            .then(data => {
              assetSelect.innerHTML = '<option value="">-- Seleccionar Equipo (Opcional) --</option>';
              data.forEach(asset => {
                const opt = document.createElement('option');
                opt.value = asset.id;
                opt.textContent = asset.name;
                assetSelect.appendChild(opt);
              });
            })
            .catch(err => {
              console.error('Error fetching assets:', err);
              assetSelect.innerHTML = '<option value="">Error al cargar equipos</option>';
            });
        } else {
          assetSelect.innerHTML = '<option value="">-- Seleccionar Equipo (Opcional) --</option>';
        }
      }
    });
  }


  // Sidebar toggle for mobile
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });
  }
});
