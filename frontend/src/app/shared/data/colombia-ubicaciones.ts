/** Departamentos y ciudades principales de Colombia, para listas de
 * direccion (registro de comprador, checkout). No es un listado DIVIPOLA
 * exhaustivo: incluye la capital de cada departamento y sus municipios
 * mas conocidos, suficiente para un formulario de envio. */
export interface DepartamentoColombia {
  nombre: string;
  ciudades: string[];
}

export const DEPARTAMENTOS_COLOMBIA: DepartamentoColombia[] = [
  { nombre: 'Amazonas', ciudades: ['Leticia', 'Puerto Nariño'] },
  { nombre: 'Antioquia', ciudades: ['Medellín', 'Bello', 'Envigado', 'Itagüí', 'Rionegro', 'Apartadó', 'Turbo'] },
  { nombre: 'Arauca', ciudades: ['Arauca', 'Saravena', 'Tame'] },
  { nombre: 'Atlántico', ciudades: ['Barranquilla', 'Soledad', 'Malambo', 'Sabanalarga'] },
  { nombre: 'Bogotá D.C.', ciudades: ['Bogotá'] },
  { nombre: 'Bolívar', ciudades: ['Cartagena', 'Magangué', 'Turbaco'] },
  { nombre: 'Boyacá', ciudades: ['Tunja', 'Duitama', 'Sogamoso', 'Chiquinquirá'] },
  { nombre: 'Caldas', ciudades: ['Manizales', 'La Dorada', 'Chinchiná'] },
  { nombre: 'Caquetá', ciudades: ['Florencia'] },
  { nombre: 'Casanare', ciudades: ['Yopal'] },
  { nombre: 'Cauca', ciudades: ['Popayán', 'Santander de Quilichao'] },
  { nombre: 'Cesar', ciudades: ['Valledupar', 'Aguachica'] },
  { nombre: 'Chocó', ciudades: ['Quibdó'] },
  { nombre: 'Córdoba', ciudades: ['Montería', 'Lorica', 'Cereté'] },
  { nombre: 'Cundinamarca', ciudades: ['Soacha', 'Zipaquirá', 'Chía', 'Facatativá', 'Girardot'] },
  { nombre: 'Guainía', ciudades: ['Inírida'] },
  { nombre: 'Guaviare', ciudades: ['San José del Guaviare'] },
  { nombre: 'Huila', ciudades: ['Neiva', 'Pitalito'] },
  { nombre: 'La Guajira', ciudades: ['Riohacha', 'Maicao'] },
  { nombre: 'Magdalena', ciudades: ['Santa Marta', 'Ciénaga'] },
  { nombre: 'Meta', ciudades: ['Villavicencio', 'Acacías'] },
  { nombre: 'Nariño', ciudades: ['Pasto', 'Tumaco', 'Ipiales'] },
  { nombre: 'Norte de Santander', ciudades: ['Cúcuta', 'Ocaña', 'Pamplona'] },
  { nombre: 'Putumayo', ciudades: ['Mocoa', 'Puerto Asís'] },
  { nombre: 'Quindío', ciudades: ['Armenia', 'Calarcá'] },
  { nombre: 'Risaralda', ciudades: ['Pereira', 'Dosquebradas', 'Santa Rosa de Cabal'] },
  { nombre: 'San Andrés y Providencia', ciudades: ['San Andrés', 'Providencia'] },
  { nombre: 'Santander', ciudades: ['Bucaramanga', 'Floridablanca', 'Girón', 'Piedecuesta', 'Barrancabermeja'] },
  { nombre: 'Sucre', ciudades: ['Sincelejo', 'Corozal'] },
  { nombre: 'Tolima', ciudades: ['Ibagué', 'Espinal'] },
  { nombre: 'Valle del Cauca', ciudades: ['Cali', 'Palmira', 'Buenaventura', 'Tuluá', 'Cartago'] },
  { nombre: 'Vaupés', ciudades: ['Mitú'] },
  { nombre: 'Vichada', ciudades: ['Puerto Carreño'] },
];
